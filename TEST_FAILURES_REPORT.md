# 香港PII识别器测试失败报告

生成时间: 2026-04-20

## 问题描述

运行 `test_hk_pii.py` 测试套件后发现多个识别器需要改进的问题。

## 测试统计

- **总计**: 11个测试模块
- **通过**: 3个 (大陆区分、混合内容、性能测试)
- **失败**: 8个
- **整体通过率**: 27.3%

## 详细失败项

### 1. 香港英文姓名识别 (HK_NAME)

**缺失的上下文关键词:**

| 语言 | 缺失关键词 |
|------|-----------|
| 简体 | `客户` |
| 繁体 | `顧客`、`持有人` |
| 英文 | `User`、`Account Holder`、`Applicant`、`Representative` |

**示例失败:**
```
✗ [简体][客户上下文] '客户：Chan Tai Man' → 未检测到香港姓名
✗ [繁体][顧客上下文] '顧客：Ho Ka Yan' → 未检测到香港姓名
✗ [繁体][持有人上下文] '持有人：Yip Tsz Chun' → 未检测到香港姓名
✗ [英文][User上下文] 'User: Cheung Ka Keung' → 未检测到香港姓名
✗ [英文][Account Holder] 'Account Holder: Wong Siu Ming' → 未检测到香港姓名
✗ [英文][Applicant] 'Applicant: Cheung Wai Man' → 未检测到香港姓名
✗ [英文][Representative] 'Representative: Lam Ka Ho' → 未检测到香港姓名
```

### 2. 香港电话识别 (HK_PHONE_NUMBER)

**不支持的格式:**

| 格式 | 示例 | 状态 |
|------|------|------|
| 连字符分隔 | `9123-4567` | ❌ 未识别 |
| 国际格式无空格 | `+85291234567` | ❌ 未识别 |
| 区号无分隔符 | `85291234567` | ❌ 未识别 |

### 3. 香港身份证识别 (HK_ID_CARD)

**校验码字母范围不完整:**

| 测试用例 | 问题 |
|----------|------|
| `B654321(B)` | 括号内字母B未被识别 |
| `S000000(B)` | S开头未被识别 |
| `VZ789012(B)` | VZ组合，括号内B未被识别 |

### 4. 脱敏功能

**英文场景占位符问题:**

| 原文 | 实际结果 | 期望结果 |
|------|---------|---------|
| `Mobile: 91234567` | `Mobile: <香港电话>` | `Mobile: <HK_PHONE_NUMBER>` |
| `HKID: A123456(7)` | `HKID: <香港身份证>` | `HKID: <HK_ID_CARD>` |
| `Name: Wong Tai Man, Phone: 91234567` | `Name: <香港姓名>, Phone: <香港电话>` | `Name: <HK_NAME>, Phone: <HK_PHONE_NUMBER>` |

**问题**: 英文场景使用了简体/繁体的中文占位符，而非英文占位符。

### 5. 繁体中文模式

**缺失的上下文关键词:**

| 测试用例 | 状态 |
|----------|------|
| `顧客：Lee Chi Wai` | ❌ 未识别 |
| `持有人：Cheung Ka Keung` | ❌ 未识别 |

### 6. 通用Guardrail (UniversalPIIGuardrail)

**语言检测误判:**

| 原文 | 检测结果 | 期望结果 |
|------|---------|---------|
| `客戶姓名：Chan Tai Man` | simplified | traditional |

### 7. 边界情况

**非香港英文姓名误判:**

| 测试用例 | 问题 |
|----------|------|
| `Name: John Smith` | ❌ 错误识别为香港姓名 |
| `Name: Michael Johnson` | ❌ 错误识别为香港姓名 |
| `Contact: Peter Brown` | ❌ 错误识别为香港姓名 |
| `聯絡人：John Smith` | ❌ 错误识别为香港姓名 |

**换行分隔符:**

| 测试用例 | 状态 |
|----------|------|
| `Name:\nWong Yan Yee` | ❌ 未能识别 |

### 8. 真实场景

**快递单场景:**

| 期望实体 | 实际检测 | 状态 |
|----------|---------|------|
| HK_NAME (寄件人) | 未检测到 | ❌ 失败 |
| HK_PHONE_NUMBER | 检测到 | ✓ |
| HK_ID_CARD | 检测到 | ✓ |
| CN_PHONE_NUMBER | 检测到 | ✓ |

**其他业务场景** (银行、医院、保险、酒店等): 全部通过 ✓

## 建议改进

### 1. HKNameRecognizer - 补充上下文关键词

```python
# 简体中文上下文
"context": ["姓名", "名字", "联系人", "客户姓名", "客户"]

# 繁体中文上下文
"context": ["姓名", "名字", "聯絡人", "客戶姓名", "顧客", "持有人"]

# 英文上下文
"context": [
    "name", "customer", "contact", "client",
    "user", "account holder", "applicant", "representative",
    "contact person", "full name", "customer name", "client name"
]
```

### 2. HKPhoneRecognizer - 扩展正则表达式

```python
PATTERNS = [
    # 现有模式
    Pattern("HK_PHONE", r"\b[56789]\d{7}\b", score=0.7),
    Pattern("HK_PHONE_SPACE", r"\b[56789]\d{3}\s\d{4}\b", score=0.7),
    Pattern("HK_PHONE_INTL", r"\+852\s?\d{8}", score=0.8),
    Pattern("HK_PHONE_INTL_ALT", r"852-?\d{8}", score=0.7),
    # 新增模式
    Pattern("HK_PHONE_HYPHEN", r"\b[56789]\d{3}-\d{4}\b", score=0.7),
    Pattern("HK_PHONE_INTL_NO_SPACE", r"\+852\d{8}", score=0.8),
]
```

### 3. HKIDCardRecognizer - 修正校验码正则

```python
# 当前（可能的问题）
Pattern("HK_ID", r"[A-NP-Z]{1,2}\d{6}\([0-9A]\)", ...)

# 修正后（完整的校验码范围）
Pattern("HK_ID", r"[A-RT-Z]{1,2}\d{6}\([0-9A]\)", ...)
# 注：S可能是特殊校验码，需要确认
```

### 4. 英文脱敏占位符 - 配置更新

在 `chinese_guardrail.py` 中检查 `REDACTION_PLACEHOLDERS` 配置，确保英文场景使用英文占位符。

### 5. 香港姓氏白名单 - 防止误判

```python
# 香港常见英文姓氏
HK_SURNAMES = {
    'chan', 'cheung', 'chow', 'choy', 'chu', 'chui', 'fong', 'fu',
    'ho', 'hong', 'hung', 'kwok', 'lam', 'lau', 'lee', 'leung',
    'li', 'liao', 'lim', 'lin', 'ling', 'liu', 'lo', 'lu',
    'ma', 'mak', 'man', 'mok', 'ng', 'ngai', 'pang', 'poon',
    'see', 'sham', 'shum', 'sinn', 'sit', 'siu', 'so', 'suen',
    'sun', 'sze', 'szeto', 'tai', 'tam', 'tan', 'tang', 'ting',
    'to', 'tong', 'tsang', 'tse', 'tsoi', 'tsui', 'wai', 'wan',
    'wang', 'wong', 'woo', 'wu', 'xiao', 'xie', 'xu', 'yau',
    'yee', 'yeung', 'yim', 'yin', 'ying', 'yip', 'yiu', 'yong',
    'yu', 'yue', 'yuen', 'yung'
}

# 在识别时检查姓氏是否在白名单中
def is_hk_surname(name: str) -> bool:
    parts = name.lower().split()
    if parts:
        return parts[0] in HK_SURNAMES
    return False
```

## 相关文件

- `test_hk_pii.py` - 测试文件（406行，完整覆盖三语场景）
- `chinese_pii_recognizers.py` - 需要改进的识别器
- `chinese_guardrail.py` - Guardrail主模块和脱敏配置

## 下一步行动

- [ ] 修复 HK_NAME 上下文关键词
- [ ] 修复 HK_PHONE_NUMBER 格式支持（连字符、国际格式）
- [ ] 修复 HK_ID_CARD 校验码范围
- [ ] 修复英文脱敏占位符配置
- [ ] 添加香港姓氏白名单过滤（防止误判非香港英文姓名）
- [ ] 修复语言检测对繁体中文的误判

## 附录：测试覆盖统计

| PII类型 | 简体测试 | 繁体测试 | 英文测试 | 边界测试 |
|---------|---------|---------|---------|---------|
| HK_NAME | 5个 | 5个 | 11个 | 9个 |
| HK_PHONE_NUMBER | 6个 | 6个 | 10个 | 10个 |
| HK_ID_CARD | 7个 | 7个 | 11个 | 11个 |

总计: 约120+个测试用例，覆盖简、繁、英三语场景
