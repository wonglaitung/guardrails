"""
代理核心模块

处理请求转发、PII过滤和响应处理。
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
import httpx

from chinese_guardrail import UniversalPIIGuardrail
from .config import GatewayConfig, ModelConfig
from .stream_handler import SSEHandler

logger = logging.getLogger(__name__)


class ProxyHandler:
    """代理处理器"""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.guardrail = UniversalPIIGuardrail(
            min_score=config.filter.min_score
        )
        self.sse_handler = SSEHandler(self.guardrail)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.models.get("default", ModelConfig(name="default", base_url="")).timeout),
            http2=True,
        )
        logger.info("ProxyHandler initialized")

    async def filter_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤请求中的PII

        支持OpenAI和Claude格式的消息。
        """
        if not self.config.filter.enabled:
            return body

        filtered_body = body.copy()

        # 处理 OpenAI 格式 /v1/chat/completions
        if "messages" in filtered_body:
            messages = filtered_body["messages"]
            for msg in messages:
                if isinstance(msg, dict) and "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        msg["content"] = self.guardrail.redact(content)
                    elif isinstance(content, list):
                        # 处理多模态内容
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                item["text"] = self.guardrail.redact(item["text"])

        # 处理 Claude 格式 /v1/messages
        if "prompt" in filtered_body:
            filtered_body["prompt"] = self.guardrail.redact(filtered_body["prompt"])

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

        if not model_config:
            raise ValueError(f"Unknown model: {model_name}")

        # 构建目标URL
        path = self._get_api_path(body)
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

            # 过滤响应内容
            if self.config.filter.enabled:
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

        if not model_config:
            raise ValueError(f"Unknown model: {model_name}")

        # 构建目标URL
        path = self._get_api_path(body)
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
        """获取模型配置"""
        # 直接匹配
        if model_name in self.config.models:
            return self.config.models[model_name]

        # 尝试前缀匹配 (e.g., "gpt-4" matches "openai")
        for name, config in self.config.models.items():
            if model_name.startswith(config.name.lower()) or model_name.startswith(name):
                return config

        # 返回默认模型
        if "default" in self.config.models:
            return self.config.models["default"]

        return None

    def _get_api_path(self, body: Dict[str, Any]) -> str:
        """根据请求体确定API路径"""
        # Claude 格式
        if "prompt" in body and "messages" not in body:
            return "v1/complete"

        # OpenAI 格式（默认）
        return "v1/chat/completions"

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
        """关闭HTTP客户端"""
        await self.client.aclose()
