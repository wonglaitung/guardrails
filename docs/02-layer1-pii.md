# 02 - Layer 1: PII 规则检测层

## 概述

Layer 1 是基于 Microsoft Presidio 和自定义正则表达式的精准检测层，负责识别和脱敏格式化的敏感信息。

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Layer 1: PII 检测层                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    UniversalPIIGuardrail                        ││
│  │                    (自动语言检测)                                ││
│  │                                                                  ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             ││
│  │  │ Simplified  │  │ Traditional │  │   English   │             ││
│  │  │ Guardrail   │  │ Guardrail   │  │ Guardrail   │             ││
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             ││
│  │         │                │                │                     ││
│  │         └────────────────┼────────────────┘                     ││
│  │                          ↓                                       ││
│  │  ┌─────────────────────────────────────────────────────────────┐││
│  │  │                  Presidio Analyzer Engine                    │││
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │││
│  │  │  │   Custom    │  │   Custom    │  │   Pattern   │         │││
│  │  │  │ Recognizers │  │   Context   │  │   Matcher   │         │││
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘         │││
│  │  └─────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      PII Entity Types                           ││
│  │  ┌───────────────────┐  ┌───────────────────┐                  ││
│  │  │ CN_PHONE_NUMBER   │  │ HK_PHONE_NUMBER   │                  ││
│  │  │ CN_ID_CARD        │  │ HK_ID_CARD        │                  ││
│  │  │ CN_BANK_CARD      │  │ HK_NAME           │                  ││
│  │  │ CN_PASSPORT       │  │ EMAIL_ADDRESS     │                  ││
│  │  │ CN_LICENSE_PLATE  │  │ IP_ADDRESS        │                  ││
│  │  │ CN_SOCIAL_CREDIT  │  │ ...               │                  ││
│  │  └───────────────────┘  └───────────────────┘                  ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## 核心类

### PIIEntity

PII 实体数据类，存储检测到的敏感信息：

```python
@dataclass
class PIIEntity:
    """PII 实体信息"""
    entity_type: str      # 实体类型，如 "CN_PHONE_NUMBER"
    text: str             # 原始文本，如 "13812345678"
    start: int            # 起始位置
    end: int              # 结束位置
    score: float          # 置信度 (0.0-1.0)
```

### ChinesePIIGuardrail

核心 PII 检测与脱敏类：

```python
from chinese_guardrail import ChinesePIIGuardrail

class ChinesePIIGuardrail:
    """
    中文 PII 安全护栏
    
    Args:
        placeholders: 自定义占位符映射
        min_score: 最小置信度阈值（默认 0.5）
        script_type: 字体类型，"simplified" 或 "traditional"
        enable_name_recognition: 是否启用中文姓名识别
    """
    
    # 简体占位符
    DEFAULT_PLACEHOLDERS = {
        "CN_PHONE_NUMBER": "<手机号>",
        "CN_ID_CARD": "<身份证号>",
        "CN_BANK_CARD": "<银行卡号>",
        ...
    }
    
    # 繁体占位符
    TRADITIONAL_PLACEHOLDERS = {
        "CN_PHONE_NUMBER": "<手機號>",
        "CN_ID_CARD": "<身分證字號>",
        ...
    }
    
    def detect(self, text: str) -> List[PIIEntity]:
        """检测文本中的 PII 实体"""
        
    def redact(self, text: str, placeholder_style: str = "type") -> str:
        """对文本中的 PII 进行脱敏处理"""
        
    def check(self, text: str) -> Tuple[str, List[PIIEntity], bool]:
        """完整检查：检测并脱敏"""
        
    def validate(self, text: str) -> bool:
        """验证文本是否安全（无 PII）"""
```

### UniversalPIIGuardrail

自动语言检测版本：

```python
from chinese_guardrail import UniversalPIIGuardrail

class UniversalPIIGuardrail:
    """
    通用 PII 安全护栏 - 自动检测中英文并处理
    
    支持：
    - 简体中文
    - 繁体中文
    - 英文
    - 中英文混合文本
    """
    
    def _detect_script(self, text: str) -> str:
        """检测文本脚本类型: "simplified", "traditional", "english" """
        
    def detect(self, text: str) -> List[PIIEntity]:
        """检测 PII，自动识别语言"""
        
    def redact(self, text: str) -> str:
        """脱敏处理，使用对应语言的占位符"""
```

## 识别器系统

### PatternRecognizer 基类

所有自定义识别器继承自 Presidio 的 `PatternRecognizer`：

```python
from presidio_analyzer import Pattern, PatternRecognizer

class CustomRecognizer(PatternRecognizer):
    # 正则模式列表
    PATTERNS = [
        Pattern("pattern_name", r"正则表达式", score=0.9)
    ]
    
    # 上下文关键词（用于提升置信度）
    CONTEXT = ["关键词1", "关键词2"]
    
    def __init__(self):
        super().__init__(
            supported_entity="CUSTOM_PII",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",  # 必须使用 "en" 以兼容 Presidio
        )
```

### 内置识别器

#### 中国手机号识别器

```python
class ChinaMobilePhoneRecognizer(PatternRecognizer):
    """中国手机号识别器（支持简繁体）"""
    
    PATTERNS = [
        Pattern(
            name="china_mobile",
            regex=r"(?<!\d)(1[3-9]\d{9})(?!\d)",
            score=0.95
        )
    ]
    
    CONTEXT = [
        # 简体
        "手机", "电话", "联系电话", "联系方式", "手机号",
        # 繁体
        "手機", "手機號", "電話", "聯絡電話",
        # 英文
        "mobile", "phone"
    ]
```

#### 身份证号识别器

```python
class ChinaIDCardRecognizer(PatternRecognizer):
    """中国身份证号识别器"""
    
    PATTERNS = [
        # 18位身份证
        Pattern(
            name="china_id_18",
            regex=r"(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)",
            score=0.95
        ),
        # 15位身份证（旧版）
        Pattern(
            name="china_id_15",
            regex=r"(?<!\d)([1-9]\d{5}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3})(?!\d)",
            score=0.85
        )
    ]
    
    CONTEXT = [
        "身份证", "身份证号", "证件号",
        "身分證", "身分證字號",  # 繁体
        "ID", "ID number"  # 英文
    ]
```

#### 银行卡号识别器

```python
class ChinaBankCardRecognizer(PatternRecognizer):
    """中国银行卡号识别器"""
    
    PATTERNS = [
        Pattern(
            name="china_bank_card",
            regex=r"(?<!\d)(\d{16,19})(?!\d)",
            score=0.6  # 较低初始分数，依赖上下文提升
        )
    ]
    
    CONTEXT = [
        "银行卡", "银行卡号", "卡号", "账号",
        "銀行卡", "銀行卡號", "卡號",  # 繁体
        "card", "bank card", "account"
    ]
```

#### 香港身份证识别器

```python
class HongKongIDCardRecognizer(PatternRecognizer):
    """香港身份证识别器
    
    格式：
    - 单字母: A123456(7)
    - 双字母: AB123456(A)
    """
    
    PATTERNS = [
        Pattern(
            name="hk_id_single_letter",
            regex=r"(?<![A-Za-z0-9])([A-Z]\d{6}\([0-9A-Z]\))(?![A-Za-z0-9)])",
            score=0.95
        ),
        Pattern(
            name="hk_id_double_letter",
            regex=r"(?<![A-Za-z0-9])([A-Z]{2}\d{6}\([0-9A-Z]\))(?![A-Za-z0-9)])",
            score=0.95
        )
    ]
```

### 自定义识别器

添加新的 PII 识别器：

```python
# 1. 定义识别器类
class CustomRecognizer(PatternRecognizer):
    PATTERNS = [Pattern("name", r"正则表达式", score=0.9)]
    CONTEXT = ["关键词1", "关键词2"]

    def __init__(self):
        super().__init__(
            supported_entity="CUSTOM_PII",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en"
        )

# 2. 注册识别器
guardrail.analyzer.registry.add_recognizer(CustomRecognizer())

# 3. 添加占位符
DEFAULT_PLACEHOLDERS["CUSTOM_PII"] = "<自定义>"
TRADITIONAL_PLACEHOLDERS["CUSTOM_PII"] = "<自訂>"
```

## 上下文增强机制

### 工作原理

Presidio 的上下文机制通过关键词提升检测置信度：

```
原始文本: "13812345678"
基础分数: 0.95 (仅正则匹配)

带上下文: "手机号是13812345678"
增强分数: 0.95 + 0.05 = 1.0 (匹配到 "手机号" 关键词)
```

### 置信度计算

```
最终分数 = min(基础分数 + 上下文加成, 1.0)
```

上下文加成规则：
- 匹配到上下文关键词: +0.05
- 多个关键词: 累加，上限 +0.1
- 无上下文: 0

## 去重机制

检测到的实体可能重叠，需要去重：

```python
def _deduplicate_entities(self, entities: List[PIIEntity]) -> List[PIIEntity]:
    """去除重叠和重复的实体"""
    # 按起始位置排序，置信度高的优先
    sorted_entities = sorted(entities, key=lambda x: (x.start, -x.score))
    
    # 去除重叠实体，保留置信度高的
    result = []
    for entity in sorted_entities:
        overlap = False
        for existing in result:
            if (entity.start < existing.end and entity.end > existing.start):
                overlap = True
                break
        if not overlap:
            result.append(entity)
    
    return result
```

## 占位符系统

### 多语言占位符

```python
# 简体中文
DEFAULT_PLACEHOLDERS = {
    "CN_PHONE_NUMBER": "<手机号>",
    "CN_ID_CARD": "<身份证号>",
    "EMAIL_ADDRESS": "<邮箱>",
}

# 繁体中文
TRADITIONAL_PLACEHOLDERS = {
    "CN_PHONE_NUMBER": "<手機號>",
    "CN_ID_CARD": "<身分證字號>",
    "EMAIL_ADDRESS": "<信箱>",
}

# 英文
ENGLISH_PLACEHOLDERS = {
    "CN_PHONE_NUMBER": "<PHONE>",
    "CN_ID_CARD": "<ID_NUMBER>",
    "EMAIL_ADDRESS": "<EMAIL>",
}
```

### 自定义占位符

```python
guardrail = ChinesePIIGuardrail(
    placeholders={
        "CN_PHONE_NUMBER": "[已脱敏]",
        "CN_ID_CARD": "***",
    }
)
```

## 脱敏样式

### type 样式（默认）

使用类型标签替换：

```python
guardrail.redact("我的手机是13812345678")
# 输出: "我的手机是<手机号>"
```

### mask 样式

使用星号遮盖：

```python
guardrail.redact("我的手机是13812345678", placeholder_style="mask")
# 输出: "我的手机是1*******8"
```

## 快捷函数

```python
from chinese_guardrail import check_pii, redact_pii, redact_pii_traditional, mask_pii, scan_pii

# 快速检查
safe_text, entities, has_pii = check_pii("我的手机是13812345678")

# 简体脱敏
safe_text = redact_pii("身份证：110101199001011234")
# 输出: "身份证：<身份证号>"

# 繁体脱敏
safe_text = redact_pii_traditional("身分證字號：110101199001011234")
# 输出: "身分證字號：<身分證字號>"

# 自动检测语言
safe_text = mask_pii("My phone is 13812345678")
# 输出: "My phone is <PHONE>"

# 完整扫描
safe_text, entities, has_pii = scan_pii("联系人：张三，电话：13912345678", lang="auto")
```

## 配置选项

```python
guardrail = ChinesePIIGuardrail(
    min_score=0.5,              # 最小置信度阈值
    script_type="simplified",   # 字体类型
    enable_name_recognition=True,  # 启用中文姓名识别
    placeholders={              # 自定义占位符
        "CN_PHONE_NUMBER": "[已脱敏]",
    }
)
```

## 性能优化

### 禁用英语 NER

默认移除 `SpacyRecognizer`，避免在中文文本上产生误报：

```python
def _register_china_recognizers(self):
    # 移除英语 NER 识别器
    for rec_name in ["SpacyRecognizer", "EmailRecognizer", "IpRecognizer"]:
        try:
            self.analyzer.registry.remove_recognizer(rec_name)
        except Exception:
            pass
```

### 使用轻量级 NLP 模型

```python
# 只加载英文小模型（用于基础分词）
nlp_config = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
}
```

## 为什么不需要中文 spaCy 模型

### 设计原理

Microsoft Presidio 有两种 PII 检测方式：

| 方式 | 原理 | 依赖 |
|------|------|------|
| **正则 + 上下文** | PatternRecognizer 匹配格式 + 关键词提升 | 无 NLP 模型 |
| **NER** | spaCy 识别命名实体 | 语言模型 |

我们选择**正则 + 上下文**方式，原因：

### 对比分析

```
┌──────────────────┬─────────────────────┬──────────────────────┐
│       方案        │   zh_core_web_sm    │    姓氏列表方案     │
├──────────────────┼─────────────────────┼──────────────────────┤
│ 中文姓名准确率   │ 约 60-70%（误报多） │ 约 90%（基于姓氏库） │
├──────────────────┼─────────────────────┼──────────────────────┤
│ 模型大小         │ ~40MB               │ 无额外依赖           │
├──────────────────┼─────────────────────┼──────────────────────┤
│ 加载时间         │ ~2秒                │ 立即                 │
├──────────────────┼─────────────────────┼──────────────────────┤
│ 检测延迟         │ ~10ms               │ <1ms                 │
└──────────────────┴─────────────────────┴──────────────────────┘
```

### 实际检测流程

当用户输入 `"我的手机号是13812345678"`：

```
1. Presidio 用 en_core_web_sm 做 tokenization（只分词）
   → ["我的", "手机", "号", "是", "13812345678"]

2. ChinaMobilePhoneRecognizer 检测正则模式
   → Pattern: 1[3-9]\d{9} 匹配 "13812345678"

3. 检查上下文关键词
   → "手机" 在 CONTEXT 列表中 → score 提升

4. 返回结果
   → PIIEntity(type="CN_PHONE_NUMBER", text="13812345678", score=0.95)
```

**全程不需要中文 NLP 模型。**

### 为什么移除 SpacyRecognizer

```python
# 移除英语 NER 识别器（在中文文本上误报严重）
default_recognizers_to_remove = [
    "EmailRecognizer",    # 用我们的 EmailRecognizerCN 替代
    "IpRecognizer",       # 用我们的 IpRecognizerCN 替代
    "SpacyRecognizer",    # 英语 NER，在中文上误报严重
]
```

**SpacyRecognizer 问题**：
- 用 `en_core_web_sm` 的 NER 在中文文本上识别实体
- 大量误报（如把"北京市"识别为人名）
- 我们的中文姓名识别器更精准

### 中文姓名识别替代方案

```python
# chinese_name_recognizer.py
COMMON_SURNAMES = set('王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗...')

def _validate_name(self, candidate: str):
    # 检查姓氏（100大姓覆盖85%人口）
    first_char = candidate[0]
    if first_char in COMMON_SURNAMES:
        return True
    # 复姓检查
    for cs in COMPOUND_SURNAMES:  # 欧阳、司马等
        if candidate.startswith(cs):
            return True
    return False
```

### 依赖总结

| 依赖 | 是否需要 | 原因 |
|------|----------|------|
| `presidio-analyzer` | ✅ 需要 | PII 检测框架 |
| `presidio-anonymizer` | ✅ 需要 | PII 脱敏功能 |
| `en_core_web_sm` | ⚠️ 内置 | Presidio 默认自带，用于基本分词 |
| `zh_core_web_sm` | ❌ 不需要 | 中文 PII 用正则+姓氏库，更精准 |
| `spaCy` | ✅ 需要 | Presidio 依赖，但只用于轻量分词 |

**核心设计理念**：用规则+上下文替代重型 NLP 模型，实现精准、快速（<1ms）的中文 PII 检测。

## 测试示例

```python
def test_pii_detection():
    guardrail = ChinesePIIGuardrail()
    
    # 手机号
    entities = guardrail.detect("我的手机是13812345678")
    assert len(entities) == 1
    assert entities[0].entity_type == "CN_PHONE_NUMBER"
    
    # 身份证
    entities = guardrail.detect("身份证号：110101199001011234")
    assert len(entities) == 1
    assert entities[0].entity_type == "CN_ID_CARD"
    
    # 多个 PII
    entities = guardrail.detect("手机13811112222，身份证110101200001011234")
    assert len(entities) == 2
```
