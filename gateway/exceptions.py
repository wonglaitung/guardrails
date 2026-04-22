"""
自定义异常类

用于 Judge 模块和其他组件的异常处理。
"""

from typing import Optional, List
from dataclasses import dataclass


@dataclass
class JudgeResult:
    """Judge 检测结果"""
    is_safe: bool
    risk_level: str  # "safe", "low", "medium", "high", "critical"
    risk_categories: List[str]
    reason: str
    confidence: float


class ContentRiskException(Exception):
    """内容风险异常 - 当 Judge 检测到高风险内容时抛出"""

    def __init__(self, result: JudgeResult, message: Optional[str] = None):
        self.result = result
        self.message = message or f"Content risk detected: {result.risk_level} - {result.reason}"
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典格式（用于 API 响应）"""
        return {
            "error": {
                "type": "content_risk",
                "message": self.message,
                "risk_level": self.result.risk_level,
                "risk_categories": self.result.risk_categories,
                "confidence": self.result.confidence,
            }
        }


class JudgeTimeoutException(Exception):
    """Judge 服务超时异常"""

    def __init__(self, timeout: float, endpoint: str):
        self.timeout = timeout
        self.endpoint = endpoint
        self.message = f"Judge service timeout after {timeout}s: {endpoint}"
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "error": {
                "type": "judge_timeout",
                "message": self.message,
                "timeout": self.timeout,
            }
        }


class JudgeUnavailableException(Exception):
    """Judge 服务不可用异常"""

    def __init__(self, endpoint: str, reason: str = "Unknown error"):
        self.endpoint = endpoint
        self.reason = reason
        self.message = f"Judge service unavailable: {endpoint} - {reason}"
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "error": {
                "type": "judge_unavailable",
                "message": self.message,
                "reason": self.reason,
            }
        }


class StreamInterruptException(Exception):
    """流式输出中断异常 - 当检测到违规内容时中断流式输出"""

    def __init__(self, reason: str, partial_content: str = ""):
        self.reason = reason
        self.partial_content = partial_content
        self.message = f"Stream interrupted: {reason}"
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "error": {
                "type": "stream_interrupted",
                "message": self.message,
                "reason": self.reason,
            }
        }
