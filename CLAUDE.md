# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chinese PII Guardrail - 基于 Microsoft Presidio 的中文敏感信息检测与脱敏方案。支持简体中文、繁体中文、英文及中英混合文本。

## Setup Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 安装中文 spaCy 模型（必需）
python -m spacy download zh_core_web_sm

# 运行测试
python chinese_guardrail.py

# 运行完整演示
python demo.py
```

## Architecture

### Two-Layer Design

1. **`chinese_pii_recognizers.py`** - PII 识别器层
   - 定义 `PatternRecognizer` 子类，每个类对应一种 PII 类型
   - 包含正则表达式模式和上下文关键词（简体+繁体）
   - 所有识别器使用 `supported_language="en"` 以兼容 Presidio 默认分析器

2. **`chinese_guardrail.py`** - Guardrail 主模块
   - `ChinesePIIGuardrail`: 核心 API，处理指定语言（简体/繁体）
   - `UniversalPIIGuardrail`: 自动语言检测，统一处理中英文
   - 快捷函数: `mask_pii()`, `scan_pii()`, `redact_pii()`, `redact_pii_traditional()`

### Key Classes

```
PIIEntity              # 数据类：存储检测到的实体信息
ChinesePIIGuardrail    # 核心 API（简体/繁体模式）
UniversalPIIGuardrail  # 自动语言检测版本
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

## Adding Custom Recognizers

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

# 注册
guardrail.analyzer.registry.add_recognizer(CustomRecognizer())
```

## Important Notes

- **语言检测**：`UniversalPIIGuardrail._detect_script()` 通过统计繁简特有字符和关键词判断语言
- **禁用英语 NER**：已移除 `SpacyRecognizer`（英语模型在中文文本上误报严重）
- **占位符**：简体/繁体/英文各有独立的占位符映射，通过 `script_type` 参数切换
- **置信度阈值**：默认 `min_score=0.5`，可通过构造函数调整
