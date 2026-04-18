# 中文 PII Guardrail

基于 Microsoft Presidio 的中文敏感信息检测与脱敏方案。

**支持简体中文、繁体中文、英文，以及中英混合文本。**

## 特性

- 🔒 **自动检测语言** - 统一入口自动识别简体/繁体/英文
- 🇨🇳 **中国特有 PII** - 手机号、身份证、银行卡、护照、车牌、统一社会信用代码
- 🌐 **多语言占位符** - 根据文本语言自动选择对应占位符
- ⚙️ **灵活配置** - 自定义占位符、置信度阈值、遮盖样式
- 🚀 **LLM 输出过滤** - 适用于大模型应用的安全护栏

## 安装

```bash
pip install -r requirements.txt

# 安装中文 spaCy 模型（必需）
python -m spacy download zh_core_web_sm
```

## 快速开始

### 统一入口（推荐）

自动检测语言并使用对应的占位符：

```python
from chinese_guardrail import scan_pii, mask_pii

# 简体中文
safe_text = mask_pii("我的手机号是13812345678")
# 输出: "我的手机号是<手机号>"

# 繁体中文
safe_text = mask_pii("我的手機號是13812345678")
# 输出: "我的手機號是<手機號>"

# 英文
safe_text = mask_pii("My phone is 13812345678")
# 输出: "My phone is <PHONE>"

# 中英混合
safe_text = mask_pii("联系人：张三，Email: zhang@test.com")
# 输出: "联系人：张三，Email: <邮箱>"
```

### 获取详细信息

```python
from chinese_guardrail import scan_pii

safe_text, entities, has_pii = scan_pii("身份证号：110101199001011234")

print(f"脱敏: {safe_text}")
# 输出: "身份证号：<身份证号>"

print(f"实体: {entities}")
# 输出: [PIIEntity(CN_ID_CARD: '110101199001011234', score=1.00)]

print(f"包含PII: {has_pii}")
# 输出: True
```

### 指定语言

```python
from chinese_guardrail import mask_pii

# 简体中文
mask_pii("手机号：13812345678", lang="zh")

# 繁体中文
mask_pii("手機號：13812345678", lang="zh-tw")

# 英文
mask_pii("Phone: 13812345678", lang="en")
```

## 支持的 PII 类型

| 类型 | 实体名称 | 示例 | 简体占位符 | 繁体占位符 |
|------|----------|------|-----------|-----------|
| 手机号 | CN_PHONE_NUMBER | 13812345678 | `<手机号>` | `<手機號>` |
| 身份证号 | CN_ID_CARD | 110101199001011234 | `<身份证号>` | `<身分證字號>` |
| 银行卡号 | CN_BANK_CARD | 6222021234567890123 | `<银行卡号>` | `<銀行卡號>` |
| 护照号 | CN_PASSPORT | E12345678 | `<护照号>` | `<護照號>` |
| 统一社会信用代码 | CN_SOCIAL_CREDIT_CODE | 91110108MA01234567 | `<统一社会信用代码>` | `<統一社會信用代碼>` |
| 车牌号 | CN_LICENSE_PLATE | 京A12345 | `<车牌号>` | `<車牌號>` |
| 邮箱 | EMAIL_ADDRESS | zhang@example.com | `<邮箱>` | `<信箱>` |
| IP地址 | IP_ADDRESS | 192.168.1.1 | `<IP地址>` | `<IP位址>` |

## 高级用法

### UniversalPIIGuardrail 类

```python
from chinese_guardrail import UniversalPIIGuardrail

guardrail = UniversalPIIGuardrail()

# 检测 PII
entities = guardrail.detect("身份证号：110101199001011234")

# 脱敏处理
safe_text = guardrail.redact("银行卡号：6222021234567890123")

# 完整检查
safe_text, entities, has_pii = guardrail.check("手机：13812345678")

# 验证文本安全性
is_safe = guardrail.validate("这是一段普通文本")  # True
is_safe = guardrail.validate("手机：13812345678")  # False
```

### 自定义配置

```python
from chinese_guardrail import create_guardrail

# 自定义占位符
custom_placeholders = {
    "CN_PHONE_NUMBER": "[电话已隐藏]",
    "CN_ID_CARD": "[身份证已隐藏]",
}

guardrail = create_guardrail(
    placeholders=custom_placeholders,
    min_score=0.7  # 置信度阈值
)

safe_text = guardrail.redact("手机号：13812345678")
# 输出: "手机号：[电话已隐藏]"
```

### 星号遮盖模式

```python
from chinese_guardrail import ChinesePIIGuardrail

guardrail = ChinesePIIGuardrail()

# 类型标签模式
safe_text = guardrail.redact("银行卡号：6222021234567890123")
# 输出: "银行卡号：<银行卡号>"

# 星号遮盖模式
safe_text = guardrail.redact("银行卡号：6222021234567890123", placeholder_style="mask")
# 输出: "银行卡号：6*****************3"
```

### 简体/繁体中文模式

```python
from chinese_guardrail import ChinesePIIGuardrail, redact_pii, redact_pii_traditional

# 简体中文
guardrail_sc = ChinesePIIGuardrail(script_type="simplified")
safe_text = guardrail_sc.redact("手机号是13812345678")
# 输出: "手机号是<手机号>"

# 繁体中文
guardrail_tc = ChinesePIIGuardrail(script_type="traditional")
safe_text = guardrail_tc.redact("手機號是13812345678")
# 输出: "手機號是<手機號>"

# 快捷函数
safe_text = redact_pii("身份证号：110101199001011234")
safe_text = redact_pii_traditional("身分證字號：110101199001011234")
```

## LLM 输出过滤

作为大模型应用输出层的安全护栏：

```python
from chinese_guardrail import UniversalPIIGuardrail

guardrail = UniversalPIIGuardrail()

def filter_llm_output(output: str) -> str:
    """过滤 LLM 输出中的敏感信息"""
    return guardrail.redact(output)

# 示例
response = filter_llm_output("根据记录，用户手机号是13812345678，已发送至邮箱zhang@test.com")
# 输出: "根据记录，用户手机号是<手机号>，已发送至邮箱<邮箱>"
```

## 扩展自定义识别器

```python
from presidio_analyzer import Pattern, PatternRecognizer
from chinese_guardrail import ChinesePIIGuardrail

class CustomRecognizer(PatternRecognizer):
    """自定义识别器示例"""
    
    PATTERNS = [
        Pattern(
            name="custom_pattern",
            regex=r"你的正则表达式",
            score=0.9
        )
    ]
    
    # 简体 + 繁体上下文关键词
    CONTEXT = ["关键词1", "关键词2", "關鍵詞"]

    def __init__(self):
        super().__init__(
            supported_entity="CUSTOM_PII",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en"  # 必须使用 "en"
        )

# 注册到 guardrail
guardrail = ChinesePIIGuardrail()
guardrail.analyzer.registry.add_recognizer(CustomRecognizer())
```

## API 参考

### 快捷函数

| 函数 | 说明 | 返回值 |
|------|------|--------|
| `mask_pii(text, lang="auto")` | 快速脱敏 | `str` |
| `scan_pii(text, lang="auto")` | 完整扫描 | `Tuple[str, List[PIIEntity], bool]` |
| `redact_pii(text)` | 简体中文脱敏 | `str` |
| `redact_pii_traditional(text)` | 繁体中文脱敏 | `str` |

### 语言参数

| 值 | 说明 |
|----|------|
| `"auto"` | 自动检测（默认） |
| `"zh"` | 简体中文 |
| `"zh-tw"` | 繁体中文 |
| `"en"` | 英文 |

### ChinesePIIGuardrail

```python
ChinesePIIGuardrail(
    placeholders=None,      # 自定义占位符映射
    min_score=0.5,          # 最小置信度阈值
    script_type="simplified" # "simplified" 或 "traditional"
)
```

### UniversalPIIGuardrail

```python
UniversalPIIGuardrail(
    placeholders=None,      # 自定义占位符映射
    min_score=0.5,          # 最小置信度阈值
    default_lang="auto"     # 默认语言
)
```

## 文件结构

```
/data/guardrails/
├── chinese_pii_recognizers.py  # PII 识别器模块
├── chinese_guardrail.py         # 主模块
├── demo.py                      # 使用示例
├── requirements.txt             # 依赖
├── README.md                    # 说明文档
└── CLAUDE.md                    # 开发指南
```

## 运行示例

```bash
# 运行完整演示
python demo.py

# 运行测试
python chinese_guardrail.py
```

## 注意事项

1. **中文姓名识别**：当前版本暂不支持中文姓名识别（英语 spaCy NER 在中文上误报严重，已禁用）
2. **置信度阈值**：默认 `min_score=0.5`，可根据场景调整
3. **银行卡号**：由于格式不够唯一，需要上下文关键词（如"银行卡"、"卡号"）来提高准确率

## License

MIT
