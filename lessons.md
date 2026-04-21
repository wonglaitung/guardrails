# 经验教训

## Docker 构建问题

### 问题：docker-entrypoint.sh 未找到

**现象**：
```
ERROR: failed to solve: failed to compute cache key: 
"/docker-entrypoint.sh": not found
```

**原因**：`.dockerignore` 中有 `docker-*.sh`，排除了入口脚本

**修复**：
```dockerignore
# Docker
Dockerfile
.dockerignore
# 注意：docker-entrypoint.sh 是容器启动必需的，不要排除
```

**教训**：`.dockerignore` 中排除模式会覆盖构建上下文，入口脚本等必需文件需要显式保留或避免匹配。

---

## 网关环境变量处理

### 问题：环境变量未传递到后台进程

**现象**：
- 配置文件中 `${ENV_VAR}` 展开为 `None`
- Pydantic 验证失败：`Input should be a valid string`

**原因**：
```python
# 错误实现 - 返回 None
def expand_env_vars(value):
    if value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, None)  # ❌ 未设置时返回 None
```

**修复**：
```python
# 正确实现 - 保持原值，由验证器过滤
def expand_env_vars(value):
    if value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value
        # 环境变量未设置，保持原样
        return value  # ✅ 保持 ${VAR} 原值

# 验证器过滤不完整配置
@field_validator("models", mode="after")
def filter_incomplete_models(cls, v):
    filtered = {}
    for name, config in v.items():
        if config.base_url and "${" in config.base_url:
            continue  # 跳过未配置的模型
        filtered[name] = config
    return filtered
```

**关键原则**：
1. 配置解析阶段：保留未展开的变量，不要返回 `None`
2. 验证阶段：过滤掉配置不完整的项，而非让整体验证失败
3. 这使得部分模型未配置时，其他模型仍能正常工作

---

## 火山方舟 API 配置

### 端点格式

**正确**：
```yaml
base_url: "https://ark.cn-beijing.volces.com/api/coding/v3"  # ✅ 包含 /v3
api_key: "${VOLCES_API_KEY}"
```

**错误**：
```yaml
base_url: "https://ark.cn-beijing.volces.com/api/coding"      # ❌ 缺少 /v3
```

### 模型名称

火山方舟使用**模型名称**（如 `glm-4.7`）而非接入点 ID，调用时：
```json
{
  "model": "glm-4.7",
  "messages": [...]
}
```

---

## LLM-as-a-Judge 概念

### 定义
**LLM-as-a-Judge**（以大模型为裁判）：用一个 LLM 来判断另一个 LLM 的内容是否安全。

```
传统规则检测：
用户输入 → 关键词/正则匹配 → 拦截/放行
（无语义理解，易被绕过）

LLM-as-a-Judge：
用户输入 → Judge LLM 理解语义 → 拦截/放行
（理解意图，难绕过）
```

### 对比示例

| 攻击方式 | 规则检测 | LLM-as-a-Judge |
|---------|---------|----------------|
| "如何制作毒品" | ✓ 关键词命中 | ✓ 语义判断 |
| "如何提纯白色粉末" | ✗ 无关键词 | ✓ 理解意图 |
| "du pin 怎么买" | ✗ 拼音绕过 | ✓ 理解含义 |
| 隐喻/反话攻击 | ✗ 无法检测 | ✓ 语义理解 |

### 适用场景划分

```
规则检测擅长（我们的项目）：
• PII 精准检测（手机、身份证、银行卡）
• 格式化数据识别
• 低延迟实时检测（<1ms）

LLM-as-a-Judge 擅长：
• 隐晦语义攻击
• 多轮对话操纵
• 角色扮演攻击
• 内容合规判断
```

### 最佳实践：组合使用

```python
class HybridGuardrail:
    def check(self, text):
        # 第一层：规则检测（快、准）
        if self.pii_guardrail.detect(text):
            return "blocked", "检测到PII"
        
        # 第二层：语义检测（理解意图）
        if not self.judge_model.is_safe(text):
            return "blocked", "内容违规"
        
        return "passed"
```

### 实现方案推荐

#### 方案一：轻量级（推荐）

使用现成的安全分类模型：

```python
from transformers import pipeline

# ShieldGemma 2B（最轻量，~100ms 延迟）
classifier = pipeline("text-classification", model="google/shieldgemma-2b")

# 提示注入专检
injection_detector = pipeline(
    "text-classification",
    model="protectai/deberta-v3-base-prompt-injection-v2"
)
```

#### 方案二：中等规模

使用 Llama Guard 3（8B），效果更好但需要 GPU。

#### 方案三：流式检测（高级）

参考 Qwen3Guard Stream，在生成过程中实时检测，发现风险立即停止。

### 实施建议

| 阶段 | 建议 |
|------|------|
| 现在 | 保持轻量，专注 PII 检测 |
| 需要内容审核 | 添加 ShieldGemma 2B（可选） |
| 需要提示注入检测 | 添加 deberta-v3-base-prompt-injection |
| 完整护栏产品 | 实现 HybridGuardrail 分层架构 |

**核心观点**：LLM-as-a-Judge 是「补充」而非「替代」，规则检测做精准匹配，语义检测做意图理解。

---

## llm-guard 实测结论

### 测试结果对比

| 测试内容 | 我们的项目 | llm-guard |
|---------|-----------|-----------|
| 大陆手机 `13812345678` | ✓ 检测 | ✗ 未检测 |
| 大陆身份证 `110101...` | ✓ 检测 | ✗ 未检测 |
| 香港身份证 `A123456(7)` | ✓ 检测 | ✗ 未检测 |
| 邮箱 | ✓ 检测 | ✓ 检测 |
| 提示词注入 | ✗ 不支持 | ✓ 检测 |
| 密钥泄露 | ✗ 不支持 | ✓ 检测 |

### 结论

**不推荐集成 llm-guard**：
1. 中文 PII 检测我们更强
2. llm-guard 使用通用 NER 模型，中文支持差
3. 体积大（需下载 ~500MB 模型）

**如需额外功能，独立实现更轻量**：
- 提示词注入：`protectai/deberta-v3-base-prompt-injection-v2`
- 密钥检测：正则表达式即可

---

## LLM 安全护栏架构设计

### 三层护栏模型（参考 NVIDIA NeMo）

| 护栏层 | 位置 | 功能 |
|--------|------|------|
| Input Rail | 用户输入前 | PII检测、提示注入检测、话题过滤 |
| Dialog Rail | 对话过程中 | 上下文追踪、语义操纵检测 |
| Output Rail | 模型输出后 | PII泄露检测、幻觉检测 |

### 主流方案对比

| 方案 | 类型 | 优势 | 适用场景 |
|------|------|------|---------|
| 规则检测（本项目） | 工具 | 精准、快速、中文优化 | PII检测 |
| llm-guard | 工具箱 | 功能全面、可插拔 | 通用防护 |
| NeMo Guardrails | 框架 | 三层架构、Colang规则 | 对话控制 |
| Llama Guard | 模型 | 语义理解、多模态 | 高级分类 |
| ShieldGemma | 模型 | 轻量级 | 边缘部署 |
| Qwen3Guard Stream | 模型 | 流式实时检测 | 在线服务 |

### 最佳实践

1. **分层防御**：规则检测（快）+ 语义检测（准）
2. **流式检测**：生成过程中实时干预，而非事后审核
3. **策略即代码**：规则可配置，无需重新训练模型

---

## 香港电话识别器设计

### 问题：如何区分香港电话和大陆手机？

**解决方案：**
- 大陆手机：11 位，以 1 开头，第二位 3-9
- 香港电话：8 位，以 5-9 开头

**正则设计：**
- 大陆: `1[3-9]\d{9}` (11 位)
- 香港: `[5-9]\d{7}` (8 位)

**注意：** 数字格式不同不会冲突，但需要确保边界检查 `(?<!\d)` 和 `(?!\d)` 防止匹配更长的数字串。

---

## 香港身份证识别器设计

### 格式特点
- 1-2 个英文字母 + 6 位数字 + 括号内校验码
- 校验码可能是数字 (0-9) 或字母 A
- 例：`A123456(7)`, `AB123456(A)`

### 正则设计
```regex
# 单字母
[A-Z]{1}\d{6}\([0-9A]\)

# 双字母
[A-Z]{2}\d{6}\([0-9A]\)
```

**注意：** 括号是香港身份证的特征，必须包含在匹配中。

---

## PII 识别器开发规范

### 1. 文件结构
- 识别器定义在 `chinese_pii_recognizers.py`
- 在 `chinese_guardrail.py` 中注册并添加占位符

### 2. 识别器模板
```python
class XxxRecognizer(PatternRecognizer):
    PATTERNS = [Pattern("name", r"regex", score=0.9)]
    CONTEXT = ["关键词1", "关键词2"]  # 简体+繁体+英文

    def __init__(self):
        super().__init__(
            supported_entity="XXX_TYPE",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en"  # 必须是 "en"
        )
```

### 3. 占位符映射
需同时更新三处：
- `DEFAULT_PLACEHOLDERS` (简体)
- `TRADITIONAL_PLACEHOLDERS` (繁体)
- `ENGLISH_PLACEHOLDERS` (英文)

### 4. 测试要点
- 正面测试：正确识别目标格式
- 负面测试：不识别相似但无效的格式
- 区分测试：确保不与其他 PII 类型混淆
- 混合测试：多种 PII 共存时的处理

---

## 常见问题

### Q: 为什么 supported_language 要用 "en"？
A: Presidio 默认分析器只支持有限语言。使用 "en" 可确保识别器被调用，同时不影响中文处理。

### Q: 如何避免误报？
A:
1. 使用上下文关键词 (CONTEXT) 提高置信度
2. 合理设置 score 阈值
3. 正则表达式使用边界检查 `(?<!\d)` `(?!\d)`

### Q: 繁简中文如何处理？
A: 在 CONTEXT 中同时包含简体和繁体关键词。例如：
```python
CONTEXT = [
    # 简体
    "身份证", "证件号",
    # 繁体
    "身份證", "證件號",
]
```
