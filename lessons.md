# 经验教训

## 可选依赖降级设计

### 问题：可选功能依赖未安装的库

**现象**：
用户未安装 `cachetools`，但代码直接导入导致崩溃。

**不好的实现**：
```python
from cachetools import TTLCache  # ❌ 未安装时直接报错

class ComplianceJudge:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=300)
```

**好的实现**：
```python
try:
    from cachetools import TTLCache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    TTLCache = None

class ComplianceJudge:
    def __init__(self):
        if HAS_CACHE:
            self._cache = TTLCache(maxsize=1000, ttl=300)
            logger.info("Judge cache enabled")
        else:
            self._cache = None
            logger.warning("cachetools not installed, cache disabled")

    async def judge(self, content: str) -> JudgeResult:
        # 使用前检查
        if self._cache is not None and cache_key in self._cache:
            return self._cache[cache_key]
        # ... 正常逻辑
```

**教训**：
1. 可选功能用 `try/except ImportError` 捕获，而非假定已安装
2. 运行时检查 `if HAS_CACHE` 而非导入时决定
3. 日志提示用户功能可用性，方便排查

---

## 缓存设计：键生成与冲突避免

### 问题：不同内容生成相同缓存键

**场景**：
- `judge(content="你好")` 返回缓存结果
- `judge(content="你好", context="上下文")` 应该是不同结果

**解决方案**：
```python
def _make_cache_key(self, content: str, context: Optional[str] = None) -> str:
    """生成缓存键 - 包含所有影响结果的因素"""
    key_data = f"{content}||{context or ''}"
    return hashlib.sha256(key_data.encode('utf-8')).hexdigest()
```

**教训**：
1. 缓存键必须包含所有影响结果的参数
2. 使用分隔符 `||` 防止 `"a||b"` 和 `"a|"` + `"b"` 冲突
3. 哈希（SHA256）可以处理任意长内容，避免键过长

---

## 异常处理：用户友好 vs 开发友好

### 问题：内部异常直接暴露给用户

**不好的实现**：
```python
# 用户看到的技术错误
{
  "error": {
    "message": "Internal server error",
    "type": "internal_error"
  }
}
```

**好的实现**：
```python
@app.exception_handler(ContentRiskException)
async def content_risk_handler(request, exc):
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "type": "content_policy_violation",
                "message": "您的内容触发安全策略限制，请修改后重试。",
                "details": {
                    "risk_level": exc.result.risk_level,
                    "risk_categories": exc.result.risk_categories,
                    "confidence": exc.result.confidence,
                },
                "suggestion": "请检查内容是否包含敏感信息或违规表述。"
            }
        }
    )
```

**教训**：
1. 用户消息：中文、友好、可操作
2. 开发调试：details 字段包含技术细节
3. 不同异常类型使用不同 HTTP 状态码，便于监控分类

### HTTP 状态码选择

| 异常类型 | 状态码 | 原因 |
|---------|-------|------|
| ContentRiskException | 400/403 | 客户端错误，用户需修改请求 |
| JudgeTimeoutException | 504 | 网关超时 |
| JudgeUnavailableException | 503 | 服务暂时不可用 |
| StreamInterruptException | 200 | 流式已部分发送 |

---

## 分层护栏架构设计

### 架构决策

```
Layer 1: 规则检测（PII）
  - 优势：精准、快速（<1ms）
  - 适用：格式化数据（手机、身份证、银行卡）
  - 实现：正则表达式 + Presidio

Layer 2: 语义检测（LLM Judge）
  - 优势：理解意图、难绕过
  - 适用：隐晦攻击、语义操纵
  - 实现：Qwen3Guard-8B-Stream

Layer 1.5: 向量风险库（可选）
  - 优势：历史风险记忆
  - 适用：已知风险模式
  - 实现：向量数据库 + 相似度匹配
```

### 执行顺序

```python
async def filter_request(self, body):
    # Layer 1: PII 过滤（必须执行）
    filtered_body = self._filter_pii(body)

    # Layer 2: Judge 检测（可选，配置启用）
    if self.judge:
        result = await self.judge.judge(user_message)
        if result.risk_level in ["high", "critical"]:
            raise ContentRiskException(result)

    return filtered_body
```

### 配置驱动

```yaml
# gateway.yaml
judge:
  enabled: false  # 默认关闭，按需启用
  timeout_action: "pass"  # 超时策略：放行 vs 阻断
```

**教训**：
1. 分层独立：Layer 1 可单独工作，Layer 2 可选增强
2. 配置驱动：通过配置开关控制，无需改代码
3. 优雅降级：Judge 不可用时不影响基础 PII 检测

---

## Docker 脚本设计：通用优于硬编码

### 问题：硬编码环境变量名不灵活

**现象**：
用户问 "docker-run.sh 支持 VOLCES_API_KEY 吗？" —— 需要手动添加每个新变量。

**不好的实现**：
```bash
# 硬编码每个变量名
if [ -n "$OPENAI_API_KEY" ]; then
    ENV_VARS="${ENV_VARS} -e OPENAI_API_KEY=${OPENAI_API_KEY}"
fi
if [ -n "$ANTHROPIC_API_KEY" ]; then
    ENV_VARS="${ENV_VARS} -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
fi
# ... 每新增一个变量都要改脚本
```

**好的实现**：
```bash
# 从配置文件自动提取变量名
if [ -f "${CONFIG_FILE}" ]; then
    VAR_NAMES=$(grep -oE '\$\{[A-Za-z_][A-Za-z0-9_]*\}' "${CONFIG_FILE}" | sed 's/[${}]//g' | sort -u)
    for var_name in $VAR_NAMES; do
        var_value="${!var_name}"
        if [ -n "$var_value" ]; then
            ENV_VARS="${ENV_VARS} -e ${var_name}=${var_value}"
        fi
    done
fi
```

**教训**：
1. 不要硬编码可变内容，从源头（配置文件）动态获取
2. 配置文件中的 `${VAR_NAME}` 就是"需要哪些变量"的声明
3. 脚本无需关心具体变量名，只负责传递

---

## 测试代码常见陷阱

### 问题：测试断言逻辑错误导致误判

**现象**：
```
✗ [换行分隔] 'Name:\nWong Yan Yee...' 未能识别
测试通过率: 90.9%
```

**调查过程**：
1. 单独测试识别器 → 正常识别
2. 使用完整 guardrail 测试 → 正常识别
3. 检查测试代码 → 发现断言逻辑错误

**根因**：
```python
# 错误代码 - 对所有用例检查同一实体类型
special_cases = [
    ("Mobile\t:\t91234567", "制表符分隔"),      # 电话
    ("Name:\nWong Yan Yee", "换行分隔"),        # 姓名 ← 检查 HK_PHONE_NUMBER
    ("Tel:  91234567", "多个空格"),              # 电话
]

for text, desc in special_cases:
    if any(e.entity_type == "HK_PHONE_NUMBER" for e in entities):  # ❌ 全检查电话
        passed += 1
```

**修复**：
```python
# 正确代码 - 每个用例指定预期类型
special_cases = [
    ("Mobile\t:\t91234567", "制表符分隔", "HK_PHONE_NUMBER"),
    ("Name:\nWong Yan Yee", "换行分隔", "HK_NAME"),      # ✓ 检查 HK_NAME
    ("Tel:  91234567", "多个空格", "HK_PHONE_NUMBER"),
]

for text, desc, expected_type in special_cases:
    if any(e.entity_type == expected_type for e in entities):  # ✓ 检查对应类型
        passed += 1
```

**教训**：
1. 测试失败时，先验证功能是否真的有问题，还是测试代码本身有 bug
2. 使用"单一职责"原则设计测试用例，避免一锅端式的断言
3. 混合类型测试时，必须为每个用例明确预期结果

---

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
