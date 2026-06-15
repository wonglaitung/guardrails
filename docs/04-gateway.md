# 04 - HTTP 代理网关

## 概述

Gateway 是一个 FastAPI 应用，提供 HTTP 代理服务，支持 OpenAI/Claude API 格式的请求转发，并集成 PII 过滤和 Judge 检测。

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HTTP Gateway                                  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      FastAPI Application                         ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             ││
│  │  │ /v1/chat/   │  │ /v1/messages│  │ /health     │             ││
│  │  │ completions │  │             │  │ /v1/models  │             ││
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘             ││
│  │         │                │                                      ││
│  └─────────┼────────────────┼──────────────────────────────────────┘│
│            │                │                                        │
│            ↓                ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      ProxyHandler                                ││
│  │                                                                  ││
│  │  ┌─────────────────────────────────────────────────────────────┐││
│  │  │                    filter_request()                          │││
│  │  │  ┌─────────────┐              ┌─────────────┐               │││
│  │  │  │   Layer 1   │              │   Layer 2   │               │││
│  │  │  │   Guardrail │     →        │   Judge     │               │││
│  │  │  │   (PII)     │              │  (可选)     │               │││
│  │  │  └─────────────┘              └─────────────┘               │││
│  │  └─────────────────────────────────────────────────────────────┘││
│  │                              ↓                                   ││
│  │  ┌─────────────────────────────────────────────────────────────┐││
│  │  │                    forward() / stream_forward()              │││
│  │  │                    (HTTP/2 客户端转发)                       │││
│  │  └─────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      Middleware                                  ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             ││
│  │  │    CORS     │  │    GZip     │  │   Lifespan  │             ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘             ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## 核心类

### ProxyHandler

代理处理器，核心业务逻辑：

```python
from gateway.proxy import ProxyHandler

class ProxyHandler:
    """
    代理处理器
    
    处理请求转发、PII 过滤和响应处理。
    支持 Layer 1 (PII规则检测) 和 Layer 2 (LLM Judge实时裁判)。
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.guardrail = UniversalPIIGuardrail(min_score=config.filter.min_score)
        self.sse_handler = SSEHandler(self.guardrail)
        self.client = httpx.AsyncClient(http2=True)
        
        # Layer 2: Judge（可选）
        self.judge = None
        self.interceptor = None
        if config.judge.enabled:
            self.judge = ComplianceJudge(config.judge)
            if config.judge.stream_intercept.enabled:
                self.interceptor = StreamInterceptor(self.judge, config.judge.stream_intercept)
    
    async def filter_request(self, body: dict, client_info: str = None) -> dict:
        """过滤请求中的 PII 并进行 Judge 检测"""
        
    async def forward(self, body: dict, headers: dict) -> dict:
        """非流式转发"""
        
    async def stream_forward(self, body: dict, headers: dict) -> AsyncGenerator[str, None]:
        """流式转发（SSE）"""
```

### 请求过滤流程

```python
async def filter_request(self, body: dict, client_info: str = None) -> dict:
    """
    过滤请求中的 PII 并进行 Judge 安全检测
    
    流程:
    1. Layer 1: PII 检测与脱敏
    2. Layer 2: Judge 安全检测（可选）
    """
    
    # Layer 1: PII 过滤
    if self.config.filter.enabled:
        if "messages" in body:  # OpenAI 格式
            for msg in body["messages"]:
                if "content" in msg:
                    entities = self.guardrail.detect(msg["content"])
                    if entities:
                        logger.warning(f"PII detected: {entities}")
                    msg["content"] = self.guardrail.redact(msg["content"])
        
        if "prompt" in body:  # Claude 格式
            entities = self.guardrail.detect(body["prompt"])
            body["prompt"] = self.guardrail.redact(body["prompt"])
    
    # Layer 2: Judge 检测
    if self.judge:
        user_message = self._extract_user_message(body)
        result = await self.judge.judge(user_message)
        
        if not result.is_safe and result.risk_level in ["high", "critical"]:
            raise ContentRiskException(result)
    
    return body
```

### 非流式转发

```python
async def forward(self, body: dict, headers: dict) -> dict:
    """
    非流式转发
    
    1. 获取模型配置
    2. 构建目标 URL
    3. 准备请求头
    4. 发送请求
    5. 过滤响应（可选）
    """
    model_name = body.get("model", "default")
    model_config = self._get_model_config(model_name)
    
    url = f"{model_config.base_url}/chat/completions"
    request_headers = self._prepare_headers(headers, model_config)
    
    response = await self.client.post(url, json=body, headers=request_headers)
    response.raise_for_status()
    
    result = response.json()
    
    # 过滤响应中的 PII（如果启用）
    if self.config.filter.filter_response:
        result = self._filter_response(result)
    
    return result
```

### 流式转发

```python
async def stream_forward(self, body: dict, headers: dict) -> AsyncGenerator[str, None]:
    """
    流式转发（SSE）
    
    1. 建立流式连接
    2. 逐行处理 SSE 数据
    3. 实时 PII 过滤
    4. 转发给客户端
    """
    model_config = self._get_model_config(body.get("model", "default"))
    url = f"{model_config.base_url}/chat/completions"
    
    async with self.client.stream("POST", url, json=body, headers=headers) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                # PII 过滤
                filtered_line = await self.sse_handler.filter_sse_line(line)
                yield filtered_line
            else:
                yield f"{line}\n\n"
```

## API 端点

### /v1/chat/completions

OpenAI 格式的聊天完成接口：

```python
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI 格式的聊天完成接口
    
    支持流式和非流式响应。
    
    请求体:
    {
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "你好"}
        ],
        "stream": false
    }
    """
    body = await request.json()
    headers = dict(request.headers)
    
    # 过滤 PII
    filtered_body = await proxy.filter_request(body, client_info)
    
    # 流式或非流式
    if filtered_body.get("stream"):
        return StreamingResponse(
            proxy.stream_forward(filtered_body, headers),
            media_type="text/event-stream"
        )
    else:
        response = await proxy.forward(filtered_body, headers)
        return JSONResponse(content=response)
```

### /v1/messages

Claude 格式的消息接口：

```python
@app.post("/v1/messages")
async def claude_messages(request: Request):
    """
    Claude 格式的聊天接口
    
    支持 Claude 3 API 格式。
    
    请求体:
    {
        "model": "claude-3-sonnet",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "你好"}
        ]
    }
    """
```

### /v1/models

列出可用模型：

```python
@app.get("/v1/models")
async def list_models():
    """
    列出可用模型
    
    返回配置文件中定义的所有模型。
    """
    models = []
    for key, model_config in config.models.items():
        models.append({
            "id": key,
            "object": "model",
            "owned_by": "gateway",
        })
    
    return {"object": "list", "data": models}
```

### /health

健康检查端点：

```python
@app.get("/health")
async def health_check():
    """
    健康检查端点
    
    返回服务状态和可用模型列表。
    """
    return HealthResponse(
        status="ok",
        models=list(config.models.keys())
    )
```

## 认证处理

### 认证模式

```python
class AuthConfig(BaseModel):
    """认证配置"""
    mode: Literal["config", "client", "both"] = "both"

# config: 只用配置文件中的 api_key
# client: 只用客户端提供的 Authorization
# both: 优先用配置文件的，如果没有则用客户端的
```

### 请求头准备

```python
def _prepare_headers(self, headers: dict, model_config: ModelConfig) -> dict:
    """准备请求头，根据 auth.mode 决定使用哪个 API Key"""
    result = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    auth_mode = self.config.auth.mode
    config_api_key = model_config.api_key
    client_auth = headers.get("authorization")
    
    if auth_mode == "config":
        if config_api_key:
            result["Authorization"] = f"Bearer {config_api_key}"
    
    elif auth_mode == "client":
        if client_auth:
            result["Authorization"] = client_auth
    
    else:  # both
        if config_api_key:
            result["Authorization"] = f"Bearer {config_api_key}"
        elif client_auth:
            result["Authorization"] = client_auth
    
    return result
```

## 多模型支持

### 模型配置

```yaml
# configs/gateway.yaml
models:
  gpt-4:
    name: "gpt-4"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    timeout: 60.0
    api_type: "openai"
  
  claude-3:
    name: "claude-3-sonnet"
    base_url: "https://api.anthropic.com/v1"
    api_key: "${ANTHROPIC_API_KEY}"
    api_type: "claude"
    custom_headers:
      "anthropic-version": "2023-06-01"
```

### 模型选择

```python
def _get_model_config(self, model_name: str) -> ModelConfig:
    """获取模型配置 - 完全按模型名直接匹配"""
    if model_name in self.config.models:
        return self.config.models[model_name]
    
    raise ValueError(f"Unknown model: {model_name}")
```

## 异常处理

### 全局异常处理器

```python
@app.exception_handler(ContentRiskException)
async def content_risk_exception_handler(request: Request, exc: ContentRiskException):
    """内容风险异常处理"""
    status_code = 400 if exc.result.risk_level in ["low", "medium"] else 403
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": "content_policy_violation",
                "message": "您的内容触发安全策略限制，请修改后重试。",
                "details": {
                    "risk_level": exc.result.risk_level,
                    "risk_categories": exc.result.risk_categories,
                    "confidence": round(exc.result.confidence, 2),
                }
            }
        }
    )


@app.exception_handler(JudgeTimeoutException)
async def judge_timeout_exception_handler(request: Request, exc: JudgeTimeoutException):
    """Judge 服务超时异常处理"""
    return JSONResponse(
        status_code=504,
        content={
            "error": {
                "type": "judge_timeout",
                "message": "安全审核服务响应超时，请稍后重试。",
            }
        }
    )
```

## 生命周期管理

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global config, proxy
    
    # 启动时
    config = load_config()
    proxy = ProxyHandler(config)
    
    logger.info(f"Gateway started on {config.server.host}:{config.server.port}")
    
    yield
    
    # 关闭时
    if proxy:
        await proxy.close()
    logger.info("Gateway stopped")
```

## 中间件配置

```python
# GZip 压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 请求示例

### OpenAI 格式（非流式）

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "我的手机号是13812345678"}
    ]
  }'
```

### OpenAI 格式（流式）

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "stream": true
  }'
```

### Claude 格式

```bash
curl -X POST http://localhost:8080/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "model": "claude-3-sonnet",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

## 性能优化

### HTTP/2 支持

```python
self.client = httpx.AsyncClient(
    http2=True,  # 启用 HTTP/2
    timeout=httpx.Timeout(60.0),
)
```

### 连接复用

```python
# 在 lifespan 中创建和关闭客户端
async def lifespan(app: FastAPI):
    proxy = ProxyHandler(config)
    yield
    await proxy.close()  # 正确关闭连接
```

### 响应过滤控制

```yaml
filter:
  filter_response: false  # 默认关闭响应过滤（只保护用户输入）
```
