"""
Pydantic模型定义

定义API请求和响应的数据模型。
"""

from typing import List, Dict, Optional, Literal, Any, Union
from pydantic import BaseModel, Field


# ============== OpenAI 格式模型 ==============

class OpenAIMessage(BaseModel):
    """OpenAI消息格式"""
    role: Literal["system", "user", "assistant", "function", "tool"]
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class OpenAIChatRequest(BaseModel):
    """OpenAI聊天完成请求"""
    model: str
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None


class OpenAIChoice(BaseModel):
    """OpenAI选择结果"""
    index: int
    message: Optional[OpenAIMessage] = None
    delta: Optional[Dict[str, Any]] = None  # 用于流式响应
    finish_reason: Optional[str] = None


class OpenAIUsage(BaseModel):
    """OpenAI用量统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenAIChatResponse(BaseModel):
    """OpenAI聊天完成响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: Optional[OpenAIUsage] = None


# ============== Claude 格式模型 ==============

class ClaudeContentBlock(BaseModel):
    """Claude内容块"""
    type: Literal["text", "image"]
    text: Optional[str] = None
    source: Optional[Dict[str, Any]] = None  # 图片源


class ClaudeMessage(BaseModel):
    """Claude消息格式"""
    role: Literal["user", "assistant"]
    content: Union[str, List[ClaudeContentBlock]]


class ClaudeChatRequest(BaseModel):
    """Claude聊天请求"""
    model: str
    max_tokens: int
    messages: List[ClaudeMessage]
    system: Optional[str] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


class ClaudeDelta(BaseModel):
    """Claude流式增量"""
    type: Literal["text_delta", "input_json_delta"]
    text: Optional[str] = None
    partial_json: Optional[str] = None


class ClaudeContentBlockDelta(BaseModel):
    """Claude内容块增量"""
    type: str = "content_block_delta"
    index: int
    delta: ClaudeDelta


class ClaudeUsage(BaseModel):
    """Claude用量统计"""
    input_tokens: int
    output_tokens: int


class ClaudeChatResponse(BaseModel):
    """Claude聊天响应"""
    id: str
    type: str = "message"
    role: str = "assistant"
    model: str
    content: List[ClaudeContentBlock]
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: ClaudeUsage


# ============== 通用模型 ==============

class ErrorResponse(BaseModel):
    """错误响应"""
    error: Dict[str, Any]


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "1.0.0"
    models: List[str] = Field(default_factory=list)
