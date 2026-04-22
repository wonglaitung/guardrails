"""
流式拦截器模块

实现 Token 级实时监控和熔断，用于流式响应中的内容安全检测。
"""

import logging
from typing import AsyncIterator, Optional
from dataclasses import dataclass

from .judge import ComplianceJudge
from .config import StreamInterceptConfig
from .exceptions import StreamInterruptException

logger = logging.getLogger(__name__)


@dataclass
class InterceptResult:
    """拦截结果"""
    should_stop: bool
    safety_score: float
    reason: str
    tokens_checked: int


class StreamInterceptor:
    """
    Token 级流式拦截器

    在流式输出过程中实时监控内容，检测到违规内容时立即中断。
    """

    def __init__(
        self,
        judge: ComplianceJudge,
        config: StreamInterceptConfig
    ):
        self.judge = judge
        self.config = config
        logger.info(
            f"StreamInterceptor initialized: check_interval={config.check_interval}, "
            f"safety_threshold={config.safety_threshold}"
        )

    async def intercept(
        self,
        stream: AsyncIterator[str],
        context: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        拦截流式输出，检测有害内容

        Args:
            stream: 原始 SSE 流
            context: 可选的上下文信息

        Yields:
            过滤后的 SSE 数据行

        Raises:
            StreamInterruptException: 当检测到违规内容时
        """
        buffer = ""
        token_count = 0
        check_count = 0

        async for line in stream:
            # 提取文本内容
            text = self._extract_text_from_sse(line)
            if text:
                buffer += text
                token_count += len(text.split())  # 简单的 token 计数

            # 判断是否需要检测
            should_check = (
                token_count >= self.config.min_tokens_before_check and
                token_count % self.config.check_interval == 0 and
                check_count < token_count // self.config.check_interval  # 避免重复检测
            )

            if should_check and self.config.enabled:
                check_count = token_count // self.config.check_interval
                try:
                    score = await self.judge.quick_check(buffer)

                    logger.debug(
                        f"Stream safety check #{check_count}: "
                        f"tokens={token_count}, score={score:.2f}"
                    )

                    if score < self.config.safety_threshold:
                        # 检测到风险，中断流
                        logger.warning(
                            f"Stream interrupted: score={score:.2f} < threshold={self.config.safety_threshold}, "
                            f"tokens={token_count}"
                        )
                        # 先发送中断消息
                        yield self._create_interrupt_message(score)
                        return

                except Exception as e:
                    logger.warning(f"Safety check failed: {e}, continuing stream")
                    # 检测失败时继续流（保守策略）

            # 无论是否检测，都转发原始行
            yield line

    async def check_content(self, content: str) -> InterceptResult:
        """
        检查内容安全性（非流式）

        Args:
            content: 待检查的内容

        Returns:
            InterceptResult: 检查结果
        """
        try:
            score = await self.judge.quick_check(content)
            should_stop = score < self.config.safety_threshold

            return InterceptResult(
                should_stop=should_stop,
                safety_score=score,
                reason="Content safety check" if not should_stop else "Content risk detected",
                tokens_checked=len(content.split()),
            )

        except Exception as e:
            logger.warning(f"Content check failed: {e}")
            return InterceptResult(
                should_stop=False,
                safety_score=0.5,
                reason=f"Check failed: {e}",
                tokens_checked=len(content.split()),
            )

    def _extract_text_from_sse(self, line: str) -> Optional[str]:
        """
        从 SSE 行中提取文本内容

        支持 OpenAI 和 Claude 格式的 SSE 数据。
        """
        import json

        line = line.strip()

        # 跳过空行和非数据行
        if not line or not line.startswith("data: "):
            return None

        data = line[6:]  # 去掉 "data: " 前缀

        # 跳过结束标记
        if data == "[DONE]":
            return None

        try:
            parsed = json.loads(data)

            # OpenAI 格式
            if "choices" in parsed:
                for choice in parsed["choices"]:
                    delta = choice.get("delta", {})
                    if "content" in delta:
                        return delta["content"]

            # Claude 格式
            if "delta" in parsed:
                delta = parsed["delta"]
                if "text" in delta:
                    return delta["text"]

            return None

        except json.JSONDecodeError:
            return None

    def _create_interrupt_message(self, score: float) -> str:
        """创建中断消息的 SSE 格式"""
        import json

        message = f"\n\n[内容安全警告：检测到潜在风险内容，输出已中断。安全评分：{score:.2f}]"

        # 构造 OpenAI 格式的 SSE 数据
        data = {
            "choices": [{
                "delta": {"content": message},
                "finish_reason": "content_filter",
                "index": 0,
            }],
            "object": "chat.completion.chunk",
        }

        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
