# 03 - Layer 2: LLM 实时裁判层

## 概述

Layer 2 是基于 Qwen3Guard-8B-Stream 的语义风险检测层，负责识别规则难以覆盖的语义攻击、提示词注入等风险。

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Layer 2: Judge 层                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    ComplianceJudge                               ││
│  │                                                                  ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             ││
│  │  │   HTTP/2    │  │   Cache     │  │   Prompt    │             ││
│  │  │   Client    │  │  (TTLCache) │  │  Templates  │             ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘             ││
│  │         │                │                │                     ││
│  │         └────────────────┼────────────────┘                     ││
│  │                          ↓                                       ││
│  │  ┌─────────────────────────────────────────────────────────────┐││
│  │  │                   Judge Methods                              │││
│  │  │  ┌───────────────────┐  ┌───────────────────┐               │││
│  │  │  │ judge()           │  │ quick_check()     │               │││
│  │  │  │ 完整检测          │  │ 快速分数检测      │               │││
│  │  │  │ (500-2000ms)      │  │ (200-500ms)       │               │││
│  │  │  └───────────────────┘  └───────────────────┘               │││
│  │  └─────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                  StreamInterceptor                               ││
│  │                    (流式拦截器)                                  ││
│  │                                                                  ││
│  │  ┌─────────────────────────────────────────────────────────────┐││
│  │  │                   Intercept Pipeline                         │││
│  │  │  累积 Buffer → Token 计数 → 定期检测 → 风险中断             │││
│  │  └─────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## 核心类

### JudgeResult

Judge 检测结果数据类：

```python
@dataclass
class JudgeResult:
    """Judge 检测结果"""
    is_safe: bool               # 是否安全
    risk_level: str             # 风险等级: safe/low/medium/high/critical
    risk_categories: List[str]  # 风险类别列表
    reason: str                 # 检测原因
    confidence: float           # 置信度 (0.0-1.0)
```

### RiskLevel

风险等级枚举：

```python
class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"           # 安全内容
    LOW = "low"             # 低风险
    MEDIUM = "medium"       # 中风险
    HIGH = "high"           # 高风险
    CRITICAL = "critical"   # 严重风险
```

### ComplianceJudge

核心裁判类：

```python
from gateway.judge import ComplianceJudge

class ComplianceJudge:
    """
    合规性裁判 - 与 Qwen3Guard-8B-Stream 交互
    
    Args:
        config: JudgeConfig 配置对象
    """
    
    def __init__(self, config: JudgeConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout),
            http2=True,
        )
        
        # 初始化缓存（可选）
        if HAS_CACHE:
            self._judge_cache = TTLCache(maxsize=1000, ttl=300)
            self._score_cache = TTLCache(maxsize=1000, ttl=300)
    
    async def judge(self, content: str, context: str = None) -> JudgeResult:
        """完整内容安全检测"""
        
    async def quick_check(self, content: str) -> float:
        """快速安全分数检测（用于流式拦截）"""
```

## Prompt 模板

### 快速检测 Prompt（无 CoT）

追求速度，不使用 Chain-of-Thought：

```python
FAST_JUDGE_PROMPT = """你是内容安全审核系统。请快速判断以下内容是否安全。

内容：
{content}

请直接输出 JSON 格式结果（不要输出其他内容）：
{"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}

风险类别可选：prompt_injection, harmful_content, pii_leakage, bias_discrimination, illegal_content, other"""
```

### 带上下文的检测 Prompt

用于需要结合对话历史判断的场景：

```python
CONTEXT_JUDGE_PROMPT = """你是内容安全审核系统。请结合上下文判断用户输入是否安全。

上下文：
{context}

用户输入：
{content}

请直接输出 JSON 格式结果（不要输出其他内容）：
{"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}"""
```

### 快速分数检测 Prompt

用于流式拦截，只返回一个分数：

```python
QUICK_SCORE_PROMPT = """请快速评估以下内容的安全程度，只输出一个 0-1 之间的数字（0=完全危险，1=完全安全）：

{content}

安全分数："""
```

## 检测方法

### judge() - 完整检测

```python
async def judge(self, content: str, context: Optional[str] = None) -> JudgeResult:
    """
    判断内容是否安全
    
    Args:
        content: 待检测的内容
        context: 可选的上下文信息（如对话历史）
    
    Returns:
        JudgeResult: 检测结果
    
    流程:
    1. 生成缓存键
    2. 检查缓存
    3. 构建 Prompt
    4. 调用 Judge 服务
    5. 解析 JSON 结果
    6. 存入缓存
    """
```

### quick_check() - 快速检测

```python
async def quick_check(self, content: str) -> float:
    """
    快速安全分数检测（用于流式拦截）
    
    Args:
        content: 待检测的内容
    
    Returns:
        float: 安全分数 (0-1)
            - 1.0 = 完全安全
            - 0.0 = 完全危险
            - 0.5 = 中等（检测失败时的默认值）
    
    特点:
    - 追求速度（<500ms）
    - 不返回详细分析
    - 使用极简 Prompt
    """
```

## 缓存机制

### 缓存配置

```python
# 缓存 TTL: 5 分钟
CACHE_TTL = 300

# 最大缓存条目数
CACHE_MAXSIZE = 1000

# 初始化缓存
if HAS_CACHE:
    self._judge_cache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL)
    self._score_cache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL)
```

### 缓存键生成

```python
def _make_cache_key(self, content: str, context: Optional[str] = None) -> str:
    """生成缓存键"""
    key_data = f"{content}||{context or ''}"
    return hashlib.sha256(key_data.encode('utf-8')).hexdigest()
```

### 缓存命中

```python
# 检查缓存
if self._judge_cache is not None and cache_key in self._judge_cache:
    cached_result = self._judge_cache[cache_key]
    logger.debug(f"Judge cache hit for content hash: {cache_key[:16]}...")
    return cached_result
```

### 无缓存降级

```python
try:
    from cachetools import TTLCache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    TTLCache = None
```

## 流式拦截器

### StreamInterceptor

Token 级实时监控和熔断：

```python
from gateway.stream_interceptor import StreamInterceptor

class StreamInterceptor:
    """
    Token 级流式拦截器
    
    在流式输出过程中实时监控内容，检测到违规内容时立即中断。
    
    Args:
        judge: ComplianceJudge 实例
        config: StreamInterceptConfig 配置
    """
    
    async def intercept(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        """拦截流式输出，检测有害内容"""
        
    async def check_content(self, content: str) -> InterceptResult:
        """检查内容安全性（非流式）"""
```

### InterceptResult

```python
@dataclass
class InterceptResult:
    """拦截结果"""
    should_stop: bool       # 是否应该中断
    safety_score: float     # 安全分数
    reason: str             # 原因
    tokens_checked: int     # 已检测的 token 数
```

### 拦截流程

```python
async def intercept(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """拦截流式输出"""
    buffer = ""
    token_count = 0
    
    async for line in stream:
        # 提取文本内容
        text = self._extract_text_from_sse(line)
        if text:
            buffer += text
            token_count += len(text.split())
        
        # 判断是否需要检测
        should_check = (
            token_count >= self.config.min_tokens_before_check and
            token_count % self.config.check_interval == 0
        )
        
        if should_check:
            score = await self.judge.quick_check(buffer)
            
            if score < self.config.safety_threshold:
                # 检测到风险，中断流
                yield self._create_interrupt_message(score)
                return
        
        # 转发原始行
        yield line
```

### SSE 解析

```python
def _extract_text_from_sse(self, line: str) -> Optional[str]:
    """从 SSE 行中提取文本内容"""
    line = line.strip()
    
    # 跳过非数据行
    if not line.startswith("data: "):
        return None
    
    data = line[6:]
    
    # 跳过结束标记
    if data == "[DONE]":
        return None
    
    parsed = json.loads(data)
    
    # OpenAI 格式
    if "choices" in parsed:
        delta = parsed["choices"][0].get("delta", {})
        return delta.get("content")
    
    # Claude 格式
    if "delta" in parsed:
        return parsed["delta"].get("text")
    
    return None
```

### 中断消息

```python
def _create_interrupt_message(self, score: float) -> str:
    """创建中断消息的 SSE 格式"""
    message = f"\n\n[内容安全警告：检测到潜在风险内容，输出已中断。安全评分：{score:.2f}]"
    
    data = {
        "choices": [{
            "delta": {"content": message},
            "finish_reason": "content_filter",
            "index": 0,
        }],
        "object": "chat.completion.chunk",
    }
    
    return f"data: {json.dumps(data)}\n\n"
```

## 配置选项

### JudgeConfig

```python
class JudgeConfig(BaseModel):
    """LLM Judge 配置"""
    enabled: bool = False                      # 是否启用
    endpoint: str = "http://localhost:8001/v1/chat/completions"  # Judge 服务地址
    model: str = "Qwen3Guard-8B-Stream"        # 模型名称
    timeout: float = 5.0                       # 超时时间（秒）
    confidence_threshold: float = 0.7          # 置信度阈值
    timeout_action: Literal["pass", "block"] = "pass"  # 超时策略
    stream_intercept: StreamInterceptConfig    # 流式拦截配置
```

### StreamInterceptConfig

```python
class StreamInterceptConfig(BaseModel):
    """流式拦截配置"""
    enabled: bool = True               # 是否启用
    check_interval: int = 5            # 每 N 个 token 检测一次
    safety_threshold: float = 0.3      # 安全分数阈值
    min_tokens_before_check: int = 10  # 开始检测前的最小 token 数
```

## 异常处理

### ContentRiskException

```python
class ContentRiskException(Exception):
    """内容风险异常"""
    
    def __init__(self, result: JudgeResult, message: str = None):
        self.result = result
        self.message = message or f"Content risk detected: {result.risk_level}"
    
    def to_dict(self) -> dict:
        """转换为 API 响应格式"""
        return {
            "error": {
                "type": "content_risk",
                "message": self.message,
                "risk_level": self.result.risk_level,
                "risk_categories": self.result.risk_categories,
                "confidence": self.result.confidence,
            }
        }
```

### JudgeTimeoutException

```python
class JudgeTimeoutException(Exception):
    """Judge 服务超时异常"""
    
    def __init__(self, timeout: float, endpoint: str):
        self.timeout = timeout
        self.endpoint = endpoint
        self.message = f"Judge service timeout after {timeout}s"
```

### JudgeUnavailableException

```python
class JudgeUnavailableException(Exception):
    """Judge 服务不可用异常"""
    
    def __init__(self, endpoint: str, reason: str):
        self.endpoint = endpoint
        self.reason = reason
        self.message = f"Judge service unavailable: {endpoint}"
```

## 使用示例

### 基本使用

```python
from gateway.judge import ComplianceJudge
from gateway.config import JudgeConfig

config = JudgeConfig(
    enabled=True,
    endpoint="http://localhost:8001/v1/chat/completions",
    timeout=5.0,
)

judge = ComplianceJudge(config)

# 完整检测
result = await judge.judge("你好，请帮我写一个故事")
if not result.is_safe:
    print(f"Risk detected: {result.risk_level}")

# 快速检测
score = await judge.quick_check("这是一段测试文本")
print(f"Safety score: {score}")
```

### 流式拦截

```python
from gateway.stream_interceptor import StreamInterceptor

interceptor = StreamInterceptor(judge, config.stream_intercept)

# 拦截 SSE 流
async for line in interceptor.intercept(original_stream):
    yield line  # 过滤后的流
```

### 集成到 ProxyHandler

```python
class ProxyHandler:
    def __init__(self, config: GatewayConfig):
        # 初始化 Judge（如果启用）
        if config.judge.enabled:
            self.judge = ComplianceJudge(config.judge)
            if config.judge.stream_intercept.enabled:
                self.interceptor = StreamInterceptor(self.judge, config.judge.stream_intercept)
    
    async def filter_request(self, body: dict, client_info: str = None):
        # Layer 2: Judge 检测
        if self.judge:
            user_message = self._extract_user_message(body)
            result = await self.judge.judge(user_message)
            
            if not result.is_safe and result.risk_level in ["high", "critical"]:
                raise ContentRiskException(result)
```

## 风险类别

| 类别 | 描述 |
|------|------|
| `prompt_injection` | 提示词注入攻击 |
| `harmful_content` | 有害内容（暴力、仇恨等） |
| `pii_leakage` | PII 泄露（Layer 1 未检测到） |
| `bias_discrimination` | 偏见与歧视 |
| `illegal_content` | 违法内容 |
| `other` | 其他风险 |

## 性能指标

| 指标 | 完整检测 | 快速检测 |
|------|----------|----------|
| 平均延迟 | 500-2000ms | 200-500ms |
| 缓存命中延迟 | <1ms | <1ms |
| 最大 Token | 256 | 10 |
| Temperature | 0.1 | 0.1 |

## 最佳实践

### 超时策略选择

```yaml
# 高安全场景：阻断请求
timeout_action: "block"

# 高可用场景：放行请求（记录日志）
timeout_action: "pass"
```

### 流式拦截调优

```yaml
stream_intercept:
  enabled: true
  check_interval: 5       # 更频繁检测 = 更安全但更慢
  safety_threshold: 0.3   # 更低阈值 = 更严格
  min_tokens_before_check: 10  # 避免开头误判
```

### 缓存优化

```python
# 高频内容场景：增大缓存
CACHE_MAXSIZE = 5000
CACHE_TTL = 600  # 10 分钟

# 低频内容场景：减少缓存
CACHE_MAXSIZE = 100
CACHE_TTL = 60  # 1 分钟
```