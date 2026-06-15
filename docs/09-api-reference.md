# 09 - API 参考

## 概述

本文档提供 Guardrails Gateway 的完整 API 参考。

## 快捷函数

### mask_pii()

自动检测语言并脱敏：

```python
from chinese_guardrail import mask_pii

safe_text = mask_pii(text: str, lang: str = "auto") -> str
```

**参数**：
- `text` (str): 待脱敏文本
- `lang` (str): 语言，"auto"（自动检测）、"zh"（简体）、"zh-tw"（繁体）、"en"（英文）

**返回**：
- `str`: 脱敏后的文本

**示例**：
```python
# 自动检测
safe_text = mask_pii("我的手机号是13812345678")
# 输出: "我的手机号是<手机号>"

# 强制语言
safe_text = mask_pii("My phone is 13812345678", lang="en")
# 输出: "My phone is <PHONE>"
```

### scan_pii()

完整扫描入口：

```python
from chinese_guardrail import scan_pii

safe_text, entities, has_pii = scan_pii(
    text: str,
    lang: str = "auto"
) -> Tuple[str, List[PIIEntity], bool]
```

**参数**：
- `text` (str): 待扫描文本
- `lang` (str): 语言设置

**返回**：
- `Tuple[str, List[PIIEntity], bool]`: (脱敏后文本, 实体列表, 是否包含PII)

**示例**：
```python
safe_text, entities, has_pii = scan_pii("手机13812345678")
if has_pii:
    for e in entities:
        print(f"发现 {e.entity_type}: {e.text}")
```

### redact_pii()

简体中文脱敏：

```python
from chinese_guardrail import redact_pii

safe_text = redact_pii(text: str) -> str
```

### redact_pii_traditional()

繁体中文脱敏：

```python
from chinese_guardrail import redact_pii_traditional

safe_text = redact_pii_traditional(text: str) -> str
```

### check_pii()

快速检查 PII：

```python
from chinese_guardrail import check_pii

safe_text, entities, has_pii = check_pii(text: str) -> Tuple[str, List[PIIEntity], bool]
```

## ChinesePIIGuardrail 类

### 初始化

```python
from chinese_guardrail import ChinesePIIGuardrail

guardrail = ChinesePIIGuardrail(
    placeholders: Optional[Dict[str, str]] = None,
    min_score: float = 0.5,
    script_type: str = "simplified",
    enable_name_recognition: bool = True,
)
```

**参数**：
- `placeholders` (Optional[Dict[str, str]]): 自定义占位符映射
- `min_score` (float): 最小置信度阈值，默认 0.5
- `script_type` (str): 字体类型，"simplified" 或 "traditional"
- `enable_name_recognition` (bool): 是否启用中文姓名识别

### detect()

检测文本中的 PII：

```python
entities = guardrail.detect(text: str, language: str = "en") -> List[PIIEntity]
```

**参数**：
- `text` (str): 待检测文本
- `language` (str): 语言代码，固定为 "en"

**返回**：
- `List[PIIEntity]`: 检测到的 PII 实体列表

### redact()

脱敏处理：

```python
safe_text = guardrail.redact(
    text: str,
    language: str = "en",
    placeholder_style: str = "type"
) -> str
```

**参数**：
- `text` (str): 待脱敏文本
- `language` (str): 语言代码
- `placeholder_style` (str): 占位符样式
  - "type": 使用类型标签（如 `<手机号>`）
  - "mask": 使用星号遮盖（如 `1*******8`）

### check()

完整检查：

```python
safe_text, entities, has_pii = guardrail.check(
    text: str,
    language: str = "en"
) -> Tuple[str, List[PIIEntity], bool]
```

### validate()

验证文本是否安全：

```python
is_safe = guardrail.validate(text: str, language: str = "en") -> bool
```

**返回**：
- `bool`: True 表示安全（无 PII），False 表示包含 PII

## UniversalPIIGuardrail 类

### 初始化

```python
from chinese_guardrail import UniversalPIIGuardrail

guardrail = UniversalPIIGuardrail(
    placeholders: Optional[Dict[str, str]] = None,
    min_score: float = 0.5,
    default_lang: str = "auto",
)
```

### detect()

自动检测语言并识别 PII：

```python
entities = guardrail.detect(text: str) -> List[PIIEntity]
```

### redact()

自动检测语言并脱敏：

```python
safe_text = guardrail.redact(text: str) -> str
```

### check()

完整检查：

```python
safe_text, entities, has_pii = guardrail.check(text: str) -> Tuple[str, List[PIIEntity], bool]
```

## PIIEntity 数据类

```python
@dataclass
class PIIEntity:
    entity_type: str  # 实体类型
    text: str         # 原始文本
    start: int        # 起始位置
    end: int          # 结束位置
    score: float      # 置信度 (0.0-1.0)
```

### 实体类型

| Entity Type | 描述 |
|-------------|------|
| `CN_PHONE_NUMBER` | 中国手机号 |
| `CN_ID_CARD` | 身份证号 |
| `CN_BANK_CARD` | 银行卡号 |
| `CN_PASSPORT` | 护照号 |
| `CN_SOCIAL_CREDIT_CODE` | 统一社会信用代码 |
| `CN_LICENSE_PLATE` | 车牌号 |
| `EMAIL_ADDRESS` | 邮箱 |
| `IP_ADDRESS` | IP 地址 |
| `HK_PHONE_NUMBER` | 香港电话 |
| `HK_ID_CARD` | 香港身份证 |
| `HK_NAME` | 香港英文姓名 |
| `PERSON` | 中文姓名（需启用） |

## ComplianceJudge 类

### 初始化

```python
from gateway.judge import ComplianceJudge
from gateway.config import JudgeConfig

config = JudgeConfig(
    enabled=True,
    endpoint="http://localhost:8001/v1/chat/completions",
    model="Qwen3Guard-8B-Stream",
    timeout=5.0,
)

judge = ComplianceJudge(config)
```

### judge()

完整内容安全检测：

```python
result = await judge.judge(
    content: str,
    context: Optional[str] = None
) -> JudgeResult
```

**参数**：
- `content` (str): 待检测内容
- `context` (Optional[str]): 可选的上下文信息

**返回**：
- `JudgeResult`: 检测结果

### quick_check()

快速安全分数检测：

```python
score = await judge.quick_check(content: str) -> float
```

**返回**：
- `float`: 安全分数 (0.0-1.0)

## JudgeResult 数据类

```python
@dataclass
class JudgeResult:
    is_safe: bool               # 是否安全
    risk_level: str             # 风险等级
    risk_categories: List[str]  # 风险类别
    reason: str                 # 检测原因
    confidence: float           # 置信度
```

### 风险等级

| 等级 | 描述 |
|------|------|
| `safe` | 安全内容 |
| `low` | 低风险 |
| `medium` | 中风险 |
| `high` | 高风险 |
| `critical` | 严重风险 |

### 风险类别

| 类别 | 描述 |
|------|------|
| `prompt_injection` | 提示词注入 |
| `harmful_content` | 有害内容 |
| `pii_leakage` | PII 泄露 |
| `bias_discrimination` | 偏见歧视 |
| `illegal_content` | 违法内容 |
| `other` | 其他 |

## StreamInterceptor 类

### intercept()

拦截流式输出：

```python
from gateway.stream_interceptor import StreamInterceptor

interceptor = StreamInterceptor(judge, config)

async for line in interceptor.intercept(stream: AsyncIterator[str]):
    yield line
```

### check_content()

检查内容安全性（非流式）：

```python
result = await interceptor.check_content(content: str) -> InterceptResult
```

## InterceptResult 数据类

```python
@dataclass
class InterceptResult:
    should_stop: bool       # 是否应该中断
    safety_score: float     # 安全分数
    reason: str             # 原因
    tokens_checked: int     # 已检测 token 数
```

## HTTP API

### POST /v1/chat/completions

OpenAI 格式聊天完成：

```http
POST /v1/chat/completions HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "stream": false
}
```

**响应**：
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "你好！有什么可以帮助你的吗？"
    },
    "finish_reason": "stop"
  }]
}
```

### POST /v1/messages

Claude 格式消息：

```http
POST /v1/messages HTTP/1.1
Host: localhost:8080
Content-Type: application/json
x-api-key: your-api-key

{
  "model": "claude-3-sonnet",
  "max_tokens": 1024,
  "messages": [
    {"role": "user", "content": "你好"}
  ]
}
```

### GET /v1/models

列出可用模型：

```http
GET /v1/models HTTP/1.1
Host: localhost:8080
```

**响应**：
```json
{
  "object": "list",
  "data": [
    {"id": "gpt-4", "object": "model", "owned_by": "gateway"},
    {"id": "claude-3", "object": "model", "owned_by": "gateway"}
  ]
}
```

### GET /health

健康检查：

```http
GET /health HTTP/1.1
Host: localhost:8080
```

**响应**：
```json
{
  "status": "ok",
  "models": ["gpt-4", "claude-3"]
}
```

## 错误响应

### ContentRiskException

```json
{
  "error": {
    "type": "content_policy_violation",
    "message": "您的内容触发安全策略限制，请修改后重试。",
    "details": {
      "risk_level": "high",
      "risk_categories": ["prompt_injection"],
      "confidence": 0.85
    }
  }
}
```

### JudgeTimeoutException

```json
{
  "error": {
    "type": "judge_timeout",
    "message": "安全审核服务响应超时，请稍后重试。",
    "details": {
      "timeout_seconds": 5.0
    }
  }
}
```

### JudgeUnavailableException

```json
{
  "error": {
    "type": "judge_unavailable",
    "message": "安全审核服务暂时不可用，请稍后重试。",
    "details": {
      "reason": "Connection refused"
    }
  }
}
```