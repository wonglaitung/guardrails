# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **经验教训**：所有关键警告和最佳实践请参阅 [lessons.md](lessons.md)
> **编程规范**：规范化开发流程、系统设计决策、测试验证要求请遵守 [docs/programmer_skill.md](docs/programmer_skill.md)

## Project Overview

Chinese PII Guardrail - 基于 Microsoft Presidio 的中文敏感信息检测与脱敏方案。支持简体中文、繁体中文、英文及中英混合文本。

**LLM Guard Gateway** - HTTP代理服务，支持OpenAI/Claude API格式，提供请求/响应PII过滤、SSE流式转发、Layer 2实时裁判。

## Setup Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 安装中文 spaCy 模型（必需）
python -m spacy download zh_core_web_sm

# 安装网关额外依赖
pip install fastapi uvicorn httpx pydantic pyyaml python-dotenv python-multipart

# 运行测试
python test_hk_pii.py          # 香港PII识别器测试
python test_gateway.py         # 网关功能测试
python chinese_guardrail.py    # 基础功能测试

# 运行完整演示
python demo.py
```

## Architecture

### Two-Layer Guardrail Design

```
请求 → Layer 1 (PII规则检测) → Layer 2 (LLM Judge) → 上游服务
              ↓                        ↓
           PII脱敏              风险检测/流式拦截
```

**Layer 1: PII规则检测**（默认启用）
- 精准、快速（<1ms）
- 适用于格式化数据（手机、身份证、银行卡）
- 实现：正则表达式 + Microsoft Presidio

**Layer 2: LLM Judge**（可选启用，配置 `judge.enabled: true`）
- 语义理解、意图判断
- 适用于隐晦攻击、语义操纵
- 实现：Qwen3Guard-8B-Stream

### Core Modules

1. **`chinese_pii_recognizers.py`** - PII 识别器层
   - 定义 `PatternRecognizer` 子类，每个类对应一种 PII 类型
   - 包含正则表达式模式和上下文关键词（简体+繁体+英文）
   - 所有识别器使用 `supported_language="en"` 以兼容 Presidio 默认分析器

2. **`chinese_guardrail.py`** - Guardrail 主模块
   - `ChinesePIIGuardrail`: 核心 API，处理指定语言（简体/繁体）
   - `UniversalPIIGuardrail`: 自动语言检测，统一处理中英文
   - 快捷函数: `mask_pii()`, `scan_pii()`, `redact_pii()`, `redact_pii_traditional()`

### Gateway Module (`gateway/`)

HTTP代理服务，支持OpenAI/Claude API格式的请求转发：

| 文件 | 功能 |
|------|------|
| `main.py` | FastAPI应用，提供 `/v1/chat/completions`, `/v1/messages` 等端点 |
| `proxy.py` | 代理核心，处理请求转发和PII过滤，协调 Layer 1/2 |
| `judge.py` | Layer 2 裁判模块，与 Qwen3Guard-8B-Stream 交互 |
| `stream_interceptor.py` | Token 级流式拦截器，实时熔断违规内容 |
| `stream_handler.py` | SSE流处理器，实时过滤流式响应中的PII |
| `config.py` | YAML配置加载，支持多模型配置和认证模式 |
| `exceptions.py` | 自定义异常类，用户友好的错误消息 |

**认证模式** (`auth.mode`):
- `config`: 只用配置文件中的 `api_key`，客户端无需提供 Authorization
- `client`: 只用客户端提供的 Authorization
- `both` (默认): 优先用配置文件的，如果没有则用客户端的

### Key Classes

```
PIIEntity              # 数据类：存储检测到的实体信息
ChinesePIIGuardrail    # 核心 API（简体/繁体模式）
UniversalPIIGuardrail  # 自动语言检测版本
ProxyHandler           # 网关代理处理器
ComplianceJudge        # Layer 2 裁判（可选）
StreamInterceptor      # Token 级流式拦截器（可选）
```

### Supported PII Types

| Entity Type | Description |
|-------------|-------------|
| CN_PHONE_NUMBER | 中国手机号 (1[3-9]\d{9}) |
| CN_ID_CARD | 身份证号 (18位/15位) |
| CN_BANK_CARD | 银行卡号 (16-19位) |
| CN_PASSPORT | 护照号 (E/G开头8位数字) |
| CN_SOCIAL_CREDIT_CODE | 统一社会信用代码 |
| CN_LICENSE_PLATE | 车牌号 |
| EMAIL_ADDRESS | 邮箱 |
| IP_ADDRESS | IP地址 |
| HK_PHONE_NUMBER | 香港电话 (8位数字，5-9开头) |
| HK_ID_CARD | 香港身份证 (如 A123456(7), AB123456(A)) |
| HK_NAME | 香港英文姓名 (基于上下文触发) |

## Running the Gateway

```bash
# 开发模式（自动重载）
./run_gateway.sh -d
# 或
uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload

# 生产模式
./run_gateway.sh -p

# 指定配置文件
./run_gateway.sh -c ./configs/gateway.yaml

# Docker 部署
./docker-build.sh && ./docker-run.sh
```

### Enabling Layer 2 Judge

编辑 `configs/gateway.yaml`:

```yaml
judge:
  enabled: true
  endpoint: "http://localhost:8001/v1/chat/completions"
  model: "Qwen3Guard-8B-Stream"
  timeout: 5.0
  timeout_action: "pass"  # pass | block
```

## Adding Custom Recognizers

1. 在 `chinese_pii_recognizers.py` 中定义识别器类：

```python
from presidio_analyzer import Pattern, PatternRecognizer

class CustomRecognizer(PatternRecognizer):
    PATTERNS = [Pattern("name", r"正则表达式", score=0.9)]
    CONTEXT = ["关键词1", "关键词2"]  # 简体+繁体

    def __init__(self):
        super().__init__(
            supported_entity="CUSTOM_PII",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en"  # 必须使用 "en"
        )
```

2. 在 `chinese_guardrail.py` 中注册并添加占位符：

```python
# 注册识别器
self.analyzer.registry.add_recognizer(CustomRecognizer())

# 更新三处占位符映射
DEFAULT_PLACEHOLDERS["CUSTOM_PII"] = "<自定义>"
TRADITIONAL_PLACEHOLDERS["CUSTOM_PII"] = "<自訂>"
ENGLISH_PLACEHOLDERS["CUSTOM_PII"] = "<CUSTOM>"
```

3. 验证：运行 `python chinese_guardrail.py` 测试识别功能

## Session Workflow

- **会话开始时**：读取 `progress.txt` 了解项目进展，审查 `lessons.md` 检查错误
- **功能更新后**：更新 `progress.txt` 记录进展，如有新学习心得更新 `lessons.md`

## Important Notes

- **语言检测**：`UniversalPIIGuardrail._detect_script()` 通过统计繁简特有字符和关键词判断语言
- **禁用英语 NER**：已移除 `SpacyRecognizer`（英语模型在中文文本上误报严重）
- **占位符**：简体/繁体/英文各有独立的占位符映射，通过 `script_type` 参数切换
- **置信度阈值**：默认 `min_score=0.5`，可通过构造函数调整
- **网关认证**：优先使用配置文件中的 `api_key`，支持三种认证模式
- **可选依赖**：`cachetools` 用于 Judge 结果缓存，未安装时自动降级为无缓存模式
- **Layer 2 独立**：Judge 模块可单独部署，通过 HTTP 与 Gateway 通信
- **流式拦截**：Token 级实时检测，检测到违规内容立即中断流式输出

## Testing

```bash
# 语法检查
python3 -m py_compile chinese_guardrail.py
python3 -m py_compile gateway/proxy.py

# PII 识别器测试
python test_hk_pii.py

# 网关功能测试
python test_gateway.py

# 基础功能测试
python chinese_guardrail.py

# 完整演示
python demo.py
```
