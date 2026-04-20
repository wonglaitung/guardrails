"""
SSE流处理器

处理Server-Sent Events格式的流式响应，并过滤其中的PII。
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SSEHandler:
    """SSE流处理器"""

    def __init__(self, guardrail):
        self.guardrail = guardrail

    @staticmethod
    def parse_sse_line(line: str) -> Optional[dict]:
        """
        解析SSE行

        Args:
            line: SSE格式的行，如 "data: {...}"

        Returns:
            解析后的JSON对象，如果是[DONE]则返回{"done": True}
        """
        if not line.startswith("data: "):
            return None

        data = line[6:]  # 去掉 "data: "

        if data == "[DONE]":
            return {"done": True}

        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse SSE data: {e}")
            return None

    @staticmethod
    def format_sse_line(data: dict) -> str:
        """
        格式化SSE行

        Args:
            data: 要格式化的数据

        Returns:
            SSE格式的行
        """
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def filter_sse_line(self, line: str) -> str:
        """
        过滤SSE行中的PII

        Args:
            line: SSE格式的行

        Returns:
            过滤后的SSE行
        """
        data = self.parse_sse_line(line)

        if data is None:
            return f"{line}\n\n"

        if data.get("done"):
            return "data: [DONE]\n\n"

        # 过滤内容
        filtered_data = self._filter_content(data)

        return self.format_sse_line(filtered_data)

    def _filter_content(self, data: dict) -> dict:
        """
        过滤数据中的PII内容

        支持OpenAI和Claude的SSE格式。
        """
        result = data.copy()

        # OpenAI 格式
        # data: {"id":"...","choices":[{"delta":{"content":"..."}}]}
        if "choices" in result:
            for choice in result["choices"]:
                # 处理 delta (流式增量)
                if "delta" in choice and "content" in choice["delta"]:
                    content = choice["delta"]["content"]
                    if isinstance(content, str):
                        choice["delta"]["content"] = self.guardrail.redact(content)

                # 处理 message (完整消息)
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    if isinstance(content, str):
                        choice["message"]["content"] = self.guardrail.redact(content)

                # 处理 text ( completions 格式)
                if "text" in choice:
                    choice["text"] = self.guardrail.redact(choice["text"])

        # Claude 格式
        # data: {"type":"content_block_delta","delta":{"text":"..."}}
        if "delta" in result and "text" in result["delta"]:
            result["delta"]["text"] = self.guardrail.redact(result["delta"]["text"])

        # Claude 新格式
        if result.get("type") == "content_block_delta":
            if "delta" in result and "text" in result["delta"]:
                result["delta"]["text"] = self.guardrail.redact(result["delta"]["text"])

        # 处理 completion 字段
        if "completion" in result:
            result["completion"] = self.guardrail.redact(result["completion"])

        return result

    def should_filter_chunk(self, data: dict) -> bool:
        """
        判断是否需要过滤这个数据块

        某些类型的数据块不需要过滤（如心跳、元数据等）。
        """
        # 跳过非内容类型的消息
        if data.get("object") in ["list", "model"]:
            return False

        # Claude 的 ping 消息
        if data.get("type") in ["ping", "message_start", "message_stop"]:
            return False

        return True
