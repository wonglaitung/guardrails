"""
代理核心模块

处理请求转发、PII过滤和响应处理。
支持 Layer 1 (PII规则检测) 和 Layer 2 (LLM Judge实时裁判)。
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
import httpx

from chinese_guardrail import UniversalPIIGuardrail
from .config import GatewayConfig, ModelConfig
from .stream_handler import SSEHandler
from .judge import ComplianceJudge
from .stream_interceptor import StreamInterceptor
from .exceptions import ContentRiskException, JudgeResult

logger = logging.getLogger(__name__)


class ProxyHandler:
    """代理处理器"""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.guardrail = UniversalPIIGuardrail(
            min_score=config.filter.min_score
        )
        self.sse_handler = SSEHandler(self.guardrail, filter_response=config.filter.filter_response)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.models.get("default", ModelConfig(name="default", base_url="")).timeout),
            http2=True,
        )

        # Layer 2: 初始化 Judge 模块
        self.judge: Optional[ComplianceJudge] = None
        self.interceptor: Optional[StreamInterceptor] = None

        if config.judge.enabled:
            self.judge = ComplianceJudge(config.judge)
            if config.judge.stream_intercept.enabled:
                self.interceptor = StreamInterceptor(self.judge, config.judge.stream_intercept)
            logger.info("Layer 2 Judge enabled")

        logger.info("ProxyHandler initialized")

    async def filter_request(self, body: Dict[str, Any], client_info: Optional[str] = None) -> Dict[str, Any]:
        """
        过滤请求中的PII并进行Judge安全检测

        Args:
            body: 请求体
            client_info: 客户端信息（IP地址等）

        支持OpenAI和Claude格式的消息。
        """
        if not self.config.filter.enabled and not self.judge:
            return body

        filtered_body = body.copy()
        client_str = f"[Client: {client_info}] " if client_info else ""

        # Layer 1: PII 过滤
        if self.config.filter.enabled:
            # 处理 OpenAI 格式 /v1/chat/completions
            if "messages" in filtered_body:
                messages = filtered_body["messages"]
                for msg in messages:
                    if isinstance(msg, dict) and "content" in msg:
                        content = msg["content"]
                        if isinstance(content, str):
                            # 检测并记录PII
                            entities = self.guardrail.detect(content)
                            if entities:
                                logger.warning(f"[PII Detected] {client_str}Request contains {len(entities)} PII entities: {[f'{e.entity_type}({e.text})' for e in entities]}")
                            msg["content"] = self.guardrail.redact(content)
                        elif isinstance(content, list):
                            # 处理多模态内容
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text = item.get("text", "")
                                    entities = self.guardrail.detect(text)
                                    if entities:
                                        logger.warning(f"[PII Detected] {client_str}Request contains {len(entities)} PII entities: {[f'{e.entity_type}({e.text})' for e in entities]}")
                                    item["text"] = self.guardrail.redact(text)

            # 处理 Claude 格式 /v1/messages
            if "prompt" in filtered_body:
                content = filtered_body["prompt"]
                entities = self.guardrail.detect(content)
                if entities:
                    logger.warning(f"[PII Detected] {client_str}Request contains {len(entities)} PII entities: {[f'{e.entity_type}({e.text})' for e in entities]}")
                filtered_body["prompt"] = self.guardrail.redact(content)

        # Layer 2: Judge 安全检测
        if self.judge:
            user_message = self._extract_user_message(filtered_body)
            if user_message:
                try:
                    result = await self.judge.judge(user_message)

                    if not result.is_safe and result.risk_level in ["high", "critical"]:
                        logger.warning(
                            f"[Judge] {client_str}High risk content detected: "
                            f"risk_level={result.risk_level}, categories={result.risk_categories}"
                        )
                        raise ContentRiskException(result)

                    logger.info(
                        f"[Judge] {client_str}Content check passed: "
                        f"risk_level={result.risk_level}, confidence={result.confidence:.2f}"
                    )

                except ContentRiskException:
                    raise
                except Exception as e:
                    logger.warning(f"[Judge] Check failed: {e}")
                    # 根据 timeout_action 决定是否阻断
                    if self.config.judge.timeout_action == "block":
                        raise

        return filtered_body

    async def forward(self, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        非流式转发

        Args:
            body: 请求体
            headers: 请求头

        Returns:
            上游服务的响应
        """
        model_name = body.get("model", "default")
        model_config = self._get_model_config(model_name)

        # 构建目标URL
        path = self._get_api_path(body, model_config.api_type)
        url = f"{model_config.base_url.rstrip('/')}/{path}"

        # 准备请求头
        request_headers = self._prepare_headers(headers, model_config)

        logger.debug(f"Forwarding request to {url}")

        try:
            response = await self.client.post(
                url,
                json=body,
                headers=request_headers,
            )
            response.raise_for_status()

            # 解析响应
            result = response.json()

            # 过滤响应内容（如果启用）
            if self.config.filter.enabled and self.config.filter.filter_response:
                result = self._filter_response(result)

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from upstream: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise

    async def stream_forward(
        self,
        body: Dict[str, Any],
        headers: Dict[str, str]
    ) -> AsyncGenerator[str, None]:
        """
        流式转发（SSE）

        Args:
            body: 请求体
            headers: 请求头

        Yields:
            SSE格式的数据行
        """
        model_name = body.get("model", "default")
        model_config = self._get_model_config(model_name)

        # 构建目标URL
        path = self._get_api_path(body, model_config.api_type)
        url = f"{model_config.base_url.rstrip('/')}/{path}"

        # 准备请求头
        request_headers = self._prepare_headers(headers, model_config)

        logger.debug(f"Streaming request to {url}")

        try:
            async with self.client.stream(
                "POST",
                url,
                json=body,
                headers=request_headers,
            ) as response:
                response.raise_for_status()

                # 流式处理响应
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # 处理 SSE 格式
                    if line.startswith("data: "):
                        # PII 过滤
                        filtered_line = await self.sse_handler.filter_sse_line(line)
                        yield filtered_line
                    else:
                        # 其他行直接转发
                        yield f"{line}\n\n"

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from upstream: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise

    def _get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """获取模型配置 - 完全按模型名直接匹配"""
        # 直接匹配模型名
        if model_name in self.config.models:
            return self.config.models[model_name]

        # 未找到匹配的配置
        logger.error(f"Unknown model: {model_name}. Available models: {list(self.config.models.keys())}")
        raise ValueError(f"Unknown model: {model_name}")

    def _extract_user_message(self, body: Dict[str, Any]) -> Optional[str]:
        """
        从请求体中提取用户消息

        支持 OpenAI 和 Claude 格式。
        """
        # OpenAI 格式
        if "messages" in body:
            messages = body["messages"]
            # 获取最后一条用户消息
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    content = msg.get("content")
                    if isinstance(content, str):
                        return content
                    elif isinstance(content, list):
                        # 多模态消息，提取文本部分
                        texts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                texts.append(item.get("text", ""))
                        return " ".join(texts)

        # Claude 格式
        if "prompt" in body:
            return body["prompt"]

        return None

    def _get_api_path(self, body: Dict[str, Any], api_type: str) -> str:
        """根据请求体确定API路径 - 只拼接 endpoint，版本号由 base_url 包含"""
        # Claude 格式
        if api_type == "claude":
            if "messages" in body:
                return "messages"  # Claude 3
            if "prompt" in body:
                return "complete"  # 旧版 Claude

        # OpenAI 格式（默认）
        return "chat/completions"

    def _prepare_headers(self, headers: Dict[str, str], model_config: ModelConfig) -> Dict[str, str]:
        """准备请求头，根据 auth.mode 决定使用哪个 API Key"""
        result = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        auth_mode = self.config.auth.mode
        config_api_key = model_config.api_key
        client_auth = headers.get("authorization") or headers.get("Authorization")

        # 根据 auth.mode 选择 API Key
        if auth_mode == "config":
            # 只用配置文件的 key
            if config_api_key:
                result["Authorization"] = f"Bearer {config_api_key}"
            else:
                logger.warning(f"Auth mode is 'config' but no api_key set for model {model_config.name}")

        elif auth_mode == "client":
            # 只用客户端的 key
            if client_auth:
                result["Authorization"] = client_auth
            else:
                logger.warning("Auth mode is 'client' but no Authorization header provided")

        else:  # auth_mode == "both" (default)
            # 优先用配置文件的，如果没有则用客户端的
            if config_api_key:
                result["Authorization"] = f"Bearer {config_api_key}"
            elif client_auth:
                result["Authorization"] = client_auth
            else:
                logger.warning("No API key available (neither config nor client provided)")

        # 添加其他必要的头
        for key in ["x-api-key", "anthropic-version"]:
            if key in headers:
                result[key] = headers[key]

        # 添加模型配置的自定义 headers（如 Host）
        if model_config.custom_headers:
            for key, value in model_config.custom_headers.items():
                result[key] = value

        return result

    def _filter_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """过滤响应内容中的PII"""
        if not self.config.filter.enabled:
            return response

        filtered = response.copy()

        # OpenAI 格式
        if "choices" in filtered:
            for choice in filtered["choices"]:
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    if isinstance(content, str):
                        choice["message"]["content"] = self.guardrail.redact(content)

                if "text" in choice:
                    choice["text"] = self.guardrail.redact(choice["text"])

        # Claude 格式
        if "completion" in filtered:
            filtered["completion"] = self.guardrail.redact(filtered["completion"])

        if "content" in filtered:
            for item in filtered["content"]:
                if isinstance(item, dict) and "text" in item:
                    item["text"] = self.guardrail.redact(item["text"])

        return filtered

    async def close(self):
        """关闭HTTP客户端和Judge客户端"""
        await self.client.aclose()
        if self.judge:
            await self.judge.close()
