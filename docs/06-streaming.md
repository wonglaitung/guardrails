# 06 - 流式处理与拦截

## 概述

流式处理模块负责处理 Server-Sent Events (SSE) 格式的响应，实现实时 PII 过滤和 Token 级安全拦截。

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Stream Processing Pipeline                       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    SSE Stream (from upstream)                    ││
│  └──────────────────────────────┬──────────────────────────────────┘│
│                                 │                                    │
│                                 ↓                                    │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    StreamInterceptor                             ││
│  │                    (Token 级拦截)                                ││
│  │                                                                  ││
│  │  ┌───────────────────────────────────────────────────────────┐ ││
│  │  │                   Intercept Loop                           │ ││
│  │  │                                                             │ ││
│  │  │   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐  │ ││
│  │  │   │ Buffer  │ → │ Token   │ → │ Check   │ → │ Decision│  │ ││
│  │  │   │ Accumu- │   │ Count   │   │ Trigger │   │  Yield  │  │ ││
│  │  │   │  lator  │   │         │   │         │   │ or Stop  │  │ ││
│  │  │   └─────────┘   └─────────┘   └─────────┘   └─────────┘  │ ││
│  │  │                                                             │ ││
│  │  └───────────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                 │                                    │
│                                 ↓                                    │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      SSEHandler                                  ││
│  │                      (PII 过滤)                                  ││
│  │                                                                  ││
│  │  ┌─────────────────┐  ┌─────────────────┐                      ││
│  │  │ parse_sse_line  │  │ filter_content  │                      ││
│  │  │ (解析 SSE)      │  │ (PII 脱敏)      │                      ││
│  │  └─────────────────┘  └─────────────────┘                      ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                 │                                    │
│                                 ↓                                    │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    SSE Stream (to client)                        ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## SSE 格式解析

### SSE 数据结构

Server-Sent Events 使用简单的文本格式：

```
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"你好"}}]}

data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"世界"}}]}

data: [DONE]
```

### OpenAI 格式

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion.chunk",
  "choices": [{
    "index": 0,
    "delta": {
      "content": "你好"
    },
    "finish_reason": null
  }]
}
```

### Claude 格式

```json
{
  "type": "content_block_delta",
  "index": 0,
  "delta": {
    "type": "text_delta",
    "text": "你好"
  }
}
```

## SSEHandler 类

### 核心方法

```python
from gateway.stream_handler import SSEHandler

class SSEHandler:
    """SSE 流处理器"""
    
    def __init__(self, guardrail, filter_response: bool = True):
        self.guardrail = guardrail
        self.filter_response = filter_response
    
    @staticmethod
    def parse_sse_line(line: str) -> Optional[dict]:
        """解析 SSE 行"""
        
    @staticmethod
    def format_sse_line(data: dict) -> str:
        """格式化 SSE 行"""
        
    async def filter_sse_line(self, line: str) -> str:
        """过滤 SSE 行中的 PII"""
```

### 解析 SSE 行

```python
@staticmethod
def parse_sse_line(line: str) -> Optional[dict]:
    """
    解析 SSE 行
    
    Args:
        line: SSE 格式的行，如 "data: {...}"
    
    Returns:
        解析后的 JSON 对象，如果是 [DONE] 返回 {"done": True}
    """
    if not line.startswith("data: "):
        return None
    
    data = line[6:]  # 去掉 "data: "
    
    if data == "[DONE]":
        return {"done": True}
    
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse SSE data")
        return None
```

### 格式化 SSE 行

```python
@staticmethod
def format_sse_line(data: dict) -> str:
    """
    格式化 SSE 行
    
    Args:
        data: 要格式化的数据
    
    Returns:
        SSE 格式的行
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
```

### 过滤 SSE 内容

```python
async def filter_sse_line(self, line: str) -> str:
    """
    过滤 SSE 行中的 PII
    
    流程:
    1. 解析 SSE 行
    2. 提取内容文本
    3. 调用 Guardrail 脱敏
    4. 重新格式化 SSE 行
    """
    data = self.parse_sse_line(line)
    
    if data is None:
        return f"{line}\n\n"
    
    if data.get("done"):
        return "data: [DONE]\n\n"
    
    # 过滤内容
    filtered_data = self._filter_content(data)
    
    return self.format_sse_line(filtered_data)
```

### 内容过滤

```python
def _filter_content(self, data: dict) -> dict:
    """
    过滤数据中的 PII 内容
    
    支持 OpenAI 和 Claude 的 SSE 格式。
    """
    if not self.filter_response:
        return data
    
    result = data.copy()
    
    # OpenAI 格式: choices[].delta.content
    if "choices" in result:
        for choice in result["choices"]:
            if "delta" in choice and "content" in choice["delta"]:
                content = choice["delta"]["content"]
                choice["delta"]["content"] = self.guardrail.redact(content)
    
    # Claude 格式: delta.text
    if "delta" in result and "text" in result["delta"]:
        result["delta"]["text"] = self.guardrail.redact(result["delta"]["text"])
    
    return result
```

## StreamInterceptor 类

### 拦截配置

```python
class StreamInterceptConfig(BaseModel):
    """流式拦截配置"""
    enabled: bool = True           # 是否启用
    check_interval: int = 5        # 每 N 个 token 检测一次
    safety_threshold: float = 0.3  # 安全分数阈值
    min_tokens_before_check: int = 10  # 开始检测前的最小 token 数
```

### 拦截流程

```python
class StreamInterceptor:
    """Token 级流式拦截器"""
    
    async def intercept(
        self,
        stream: AsyncIterator[str],
        context: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        拦截流式输出，检测有害内容
        
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
                token_count += len(text.split())
            
            # 判断是否需要检测
            should_check = (
                token_count >= self.config.min_tokens_before_check and
                token_count % self.config.check_interval == 0 and
                check_count < token_count // self.config.check_interval
            )
            
            if should_check and self.config.enabled:
                check_count = token_count // self.config.check_interval
                
                # 调用快速检测
                score = await self.judge.quick_check(buffer)
                
                logger.debug(
                    f"Safety check #{check_count}: "
                    f"tokens={token_count}, score={score:.2f}"
                )
                
                # 风险判断
                if score < self.config.safety_threshold:
                    logger.warning(
                        f"Stream interrupted: score={score:.2f} < threshold"
                    )
                    yield self._create_interrupt_message(score)
                    return
            
            # 转发原始行
            yield line
```

### SSE 文本提取

```python
def _extract_text_from_sse(self, line: str) -> Optional[str]:
    """
    从 SSE 行中提取文本内容
    
    支持 OpenAI 和 Claude 格式。
    """
    line = line.strip()
    
    # 跳过非数据行
    if not line or not line.startswith("data: "):
        return None
    
    data = line[6:]
    
    # 跳过结束标记
    if data == "[DONE]":
        return None
    
    try:
        parsed = json.loads(data)
        
        # OpenAI 格式
        if "choices" in parsed:
            delta = parsed["choices"][0].get("delta", {})
            return delta.get("content")
        
        # Claude 格式
        if "delta" in parsed:
            return parsed["delta"].get("text")
        
        return None
        
    except json.JSONDecodeError:
        return None
```

### 中断消息

```python
def _create_interrupt_message(self, score: float) -> str:
    """创建中断消息的 SSE 格式"""
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
```

## 流式转发集成

### ProxyHandler 流式转发

```python
async def stream_forward(
    self,
    body: Dict[str, Any],
    headers: Dict[str, str]
) -> AsyncGenerator[str, None]:
    """
    流式转发（SSE）
    
    流程:
    1. 建立流式连接
    2. 逐行处理 SSE 数据
    3. 可选：Token 级拦截
    4. PII 过滤
    5. 转发给客户端
    """
    model_config = self._get_model_config(body.get("model"))
    url = f"{model_config.base_url}/chat/completions"
    
    async with self.client.stream("POST", url, json=body, headers=headers) as response:
        async for line in response.aiter_lines():
            if not line:
                continue
            
            # 处理 SSE 格式
            if line.startswith("data: "):
                # PII 过滤
                filtered_line = await self.sse_handler.filter_sse_line(line)
                yield filtered_line
            else:
                yield f"{line}\n\n"
```

### FastAPI 流式响应

```python
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    
    filtered_body = await proxy.filter_request(body)
    
    if filtered_body.get("stream"):
        return StreamingResponse(
            proxy.stream_forward(filtered_body, headers),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
```

## 检测策略

### 定期检测

```python
# 每 N 个 token 检测一次
check_interval: int = 5

# 检测触发条件
should_check = (
    token_count >= min_tokens_before_check and
    token_count % check_interval == 0
)
```

### 快速检测

```python
# 使用 quick_check 方法，只返回分数
score = await self.judge.quick_check(buffer)

# 分数范围: 0.0 (危险) - 1.0 (安全)
# 阈值默认 0.3，低于阈值触发中断
if score < self.config.safety_threshold:
    # 中断流式输出
    yield interrupt_message
    return
```

### 累积缓冲

```python
# 累积已输出的文本
buffer = ""
for line in stream:
    text = extract_text(line)
    if text:
        buffer += text
    
    # 检测时使用完整缓冲区
    score = judge.quick_check(buffer)
```

## 性能优化

### 检测间隔调优

```yaml
stream_intercept:
  # 更频繁检测 = 更安全但更慢
  check_interval: 3
  
  # 更少检测 = 更快但可能漏检
  check_interval: 10
```

### 最小 Token 数

```yaml
# 避免开头误判
min_tokens_before_check: 10

# 更早开始检测
min_tokens_before_check: 5
```

### 缓存利用

```python
# Judge 缓存自动生效
# 相似内容的检测会命中缓存，延迟 < 1ms
score = await self.judge.quick_check(buffer)
```

## 异常处理

### StreamInterruptException

```python
class StreamInterruptException(Exception):
    """流式输出中断异常"""
    
    def __init__(self, reason: str, partial_content: str = ""):
        self.reason = reason
        self.partial_content = partial_content
```

### 异常处理器

```python
@app.exception_handler(StreamInterruptException)
async def stream_interrupt_exception_handler(request: Request, exc: StreamInterruptException):
    """流式输出中断异常处理"""
    return JSONResponse(
        status_code=200,  # 流式响应已部分发送
        content={
            "error": {
                "type": "stream_interrupted",
                "message": "输出内容触发安全策略，已中断。",
            }
        }
    )
```

## 调试技巧

### 检测日志

```python
logger.debug(
    f"Safety check #{check_count}: "
    f"tokens={token_count}, score={score:.2f}, "
    f"buffer_preview={buffer[:50]}..."
)
```

### 阈值测试

```python
# 测试不同阈值的效果
for threshold in [0.1, 0.3, 0.5, 0.7]:
    config.safety_threshold = threshold
    # 运行测试用例
```

### 中断模拟

```python
# 模拟中断场景
test_stream = generate_malicious_stream()
async for line in interceptor.intercept(test_stream):
    print(line)
# 应在检测到风险时中断
```