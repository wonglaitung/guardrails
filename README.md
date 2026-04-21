# 中文 PII Guardrail + LLM Gateway

基于 Microsoft Presidio 的中文敏感信息检测与脱敏方案，**新增 HTTP 代理网关**，支持 OpenAI/Claude API 格式，实现请求/响应实时 PII 过滤。

**支持简体中文、繁体中文、英文，以及中英混合文本。**

---

## 目录

- [特性](#特性)
- [快速开始](#快速开始)
- [两种使用方式](#两种使用方式)
- [使用案例](#使用案例)
  - [方式一：Python SDK（库调用）](#方式一python-sdk库调用)
  - [方式二：HTTP Gateway（代理服务）](#方式二http-gateway代理服务)
- [支持的 PII 类型](#支持的-pii-类型)
- [API 参考](#api-参考)
- [项目结构](#项目结构)
- [License](#license)

---

## 特性

### PII 检测核心
- 🔒 **自动语言检测** - 统一入口自动识别简体/繁体/英文
- 🇨🇳 **中国特有 PII** - 手机号、身份证、银行卡、护照、车牌、统一社会信用代码
- 🇭🇰 **香港 PII** - 香港电话、身份证、英文姓名识别
- 🌐 **多语言占位符** - 根据文本语言自动选择对应占位符
- ⚙️ **灵活配置** - 自定义占位符、置信度阈值、遮盖样式

### LLM Gateway（新增）
- 🚀 **API 代理** - 支持 OpenAI、Claude API 格式
- 🔄 **流式支持** - SSE 实时过滤，不中断用户体验
- 🔐 **认证管理** - 支持 config/client/both 三种认证模式
- ⚡ **异步处理** - 基于 FastAPI + httpx，高性能并发

---

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repository>
cd chinese-guardrails

# 安装依赖
pip install -r requirements.txt

# 安装中文 spaCy 模型（必需）
python -m spacy download zh_core_web_sm

# 安装网关额外依赖
pip install fastapi uvicorn httpx pydantic pyyaml
```

### 方式一：Python SDK（库调用）

```python
from chinese_guardrail import mask_pii, scan_pii

# 一键脱敏（自动识别语言）
text = "我的手机号是13812345678，身份证是110101199001011234"
safe_text = mask_pii(text)
# 输出: "我的手机号是<手机号>，身份证是<身份证号>"

# 获取详细信息
safe_text, entities, has_pii = scan_pii(text)
print(f"检测到 {len(entities)} 个实体")
for e in entities:
    print(f"  - {e.entity_type}: {e.text}")
```

### 方式二：HTTP Gateway（代理服务）

#### 1. 配置网关

编辑 `configs/gateway.yaml`：

```yaml
models:
  # OpenAI 示例
  gpt-4:
    name: "gpt-4"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    api_type: "openai"

  # 火山方舟 GLM-4.7 示例
  glm-4.7:
    name: "glm-4.7"
    base_url: "https://ark.cn-beijing.volces.com/api/coding/v3"
    api_key: "${VOLCES_API_KEY}"
    api_type: "openai"

auth:
  mode: "config"  # config: 客户端无需提供 Authorization

filter:
  enabled: true
  min_score: 0.5
  action: "redact"
```

#### 2. 启动服务

```bash
# 设置环境变量
export VOLCES_API_KEY="your-api-key"

# 启动网关
./run_gateway.sh -d  # 开发模式
```

#### 3. 使用 API

**通过网关访问（自动 PII 过滤）：**

```bash
# 客户端请求（网关自动过滤 PII 后转发）
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4.7",
    "messages": [{"role": "user", "content": "我的手机号是13812345678，身份证是110101199001011234"}]
  }'

# 实际发送给 GLM-4.7 的内容已过滤为:
# "我的手机号是<手机号>，身份证是<身份证号>"
```

**直接访问上游 API（无 PII 保护）：**

```bash
# 直接调用火山方舟 API（绕过网关，无 PII 过滤）
curl -X POST https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "glm-4.7",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

**两种访问方式对比：**

| 特性 | 直接访问上游 | 通过网关访问 |
|------|-------------|-------------|
| PII 过滤 | ❌ 无 | ✅ 自动脱敏 |
| API Key 管理 | 客户端持有 | 网关统一托管 |
| 访问控制 | 依赖上游 | 支持白名单/认证 |
| 日志审计 | ❌ 无 | ✅ 完整记录 |
| 流式响应 | ✅ 支持 | ✅ 支持 |

---

## 两种使用方式

### 方式一：Python SDK（库调用）

适用于直接集成到 Python 应用中。

#### 统一入口（推荐）

```python
from chinese_guardrail import mask_pii, scan_pii

# 简体中文
mask_pii("手机号：13812345678")  # → "手机号：<手机号>"

# 繁体中文
mask_pii("手機號：13812345678")  # → "手機號：<手機號>"

# 英文
mask_pii("Phone: 13812345678")   # → "Phone: <PHONE>"

# 中英混合
mask_pii("联系人：张三，Email: zhang@test.com")
# → "联系人：<姓名>，Email: <邮箱>"
```

#### 高级用法

```python
from chinese_guardrail import UniversalPIIGuardrail

guardrail = UniversalPIIGuardrail(min_score=0.7)

# 检测 PII
entities = guardrail.detect("身份证号：110101199001011234")

# 脱敏处理
safe_text = guardrail.redact("银行卡号：6222021234567890123")

# 验证文本安全性
is_safe = guardrail.validate("这是一段普通文本")  # True
```

### 方式二：HTTP Gateway（代理服务）

适用于为 LLM 应用提供统一入口，集中管理 API Key 和 PII 过滤。

#### 认证模式

| 模式 | 行为 | 使用场景 |
|------|------|---------|
| `config` | 只用配置文件的 `api_key` | 网关统一托管，客户端无需认证 |
| `client` | 只用客户端的 `Authorization` | 多租户，各用户自带 Key |
| `both` | 优先用配置文件，否则用客户端 | 灵活兼容两种模式 |

#### 启动服务

```bash
# 开发模式（自动重载）
./run_gateway.sh -d

# 生产模式（多进程）
./run_gateway.sh -p

# 指定配置文件
./run_gateway.sh -c ./configs/gateway.yaml
```

#### 支持的端点

- `POST /v1/chat/completions` - OpenAI 格式
- `POST /v1/messages` - Claude 格式
- `GET /health` - 健康检查
- `GET /v1/models` - 模型列表

#### 流式请求示例

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai",
    "stream": true,
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

#### Docker 部署（推荐）

使用 Docker 快速部署 Gateway 服务：

```bash
# 1. 构建镜像
docker build -t guardrails-gateway:latest .

# 2. 运行容器（火山方舟 GLM-4.7 示例）
docker run -d \
  -p 8080:8080 \
  -e VOLCES_API_KEY="your-api-key" \
  -e GATEWAY_WORKERS=2 \
  --name guardrails-gateway \
  --restart unless-stopped \
  guardrails-gateway:latest

# 3. 测试访问
curl http://localhost:8080/health
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "glm-4.7", "messages": [{"role": "user", "content": "你好"}]}'
```

**多模型配置示例：**

```bash
# 同时支持 OpenAI + 火山方舟
docker run -d \
  -p 8080:8080 \
  -e OPENAI_API_KEY="sk-openai-xxx" \
  -e VOLCES_API_KEY="your-api-key" \
  -e GATEWAY_WORKERS=4 \
  -e GATEWAY_LOG_LEVEL=info \
  --name guardrails-gateway \
  guardrails-gateway:latest
```

**支持的环境变量：**

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `GATEWAY_WORKERS` | Gunicorn worker 数量 | 4 |
| `GATEWAY_HOST` | 绑定主机 | 0.0.0.0 |
| `GATEWAY_PORT` | 绑定端口 | 8080 |
| `GATEWAY_CONFIG` | 配置文件路径 | /app/configs/gateway.yaml |
| `GATEWAY_LOG_LEVEL` | 日志级别 | warning |
| `VOLCES_API_KEY` | 火山方舟 API Key | - |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Claude API Key | - |

Docker 镜像特性：
- 多阶段构建，体积小
- 使用 Gunicorn + Uvicorn worker，生产就绪
- 内置健康检查
- 非 root 用户运行
- 支持环境变量传入 API keys

---

## 使用案例

### 案例一：火山方舟 GLM-4.7

#### 方式 A：直接访问上游 API

```bash
# 直接调用火山方舟（无 PII 保护）
curl -s https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "glm-4.7",
    "messages": [
      {"role": "user", "content": "我的手机号是13800138000，请帮我查一下余额"}
    ],
    "max_tokens": 100
  }'

# ⚠️ 注意：手机号明文发送到第三方，存在泄露风险
```

#### 方式 B：通过网关访问（推荐）

```bash
# 1. 启动网关
export VOLCES_API_KEY="your-api-key"
./run_gateway.sh -d

# 2. 通过网关调用（自动 PII 过滤）
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4.7",
    "messages": [
      {"role": "user", "content": "我的手机号是13800138000，请帮我查一下余额"}
    ],
    "max_tokens": 100
  }'

# ✅ 实际发送到 GLM-4.7 的内容：
# "我的手机号是<手机号>，请帮我查一下余额"
```

### 案例二：混合场景（OpenAI + 火山方舟）

```yaml
# configs/gateway.yaml
models:
  gpt-4:
    name: "gpt-4"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    api_type: "openai"

  glm-4.7:
    name: "glm-4.7"
    base_url: "https://ark.cn-beijing.volces.com/api/coding/v3"
    api_key: "${VOLCES_API_KEY}"
    api_type: "openai"
```

```bash
# 同一网关，切换不同上游模型

# 调用 OpenAI GPT-4
curl http://localhost:8080/v1/chat/completions \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "你好"}]}'

# 调用火山方舟 GLM-4.7
curl http://localhost:8080/v1/chat/completions \
  -d '{"model": "glm-4.7", "messages": [{"role": "user", "content": "你好"}]}'

# 两个请求都经过相同的 PII 过滤处理
```

### 案例三：流式响应

```bash
# 通过网关使用流式响应（SSE）
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4.7",
    "messages": [{"role": "user", "content": "我的邮箱是zhangsan@example.com"}],
    "stream": true
  }'

# 流式响应中，PII 同样会被实时过滤
```

---

## 支持的 PII 类型

| 类型 | 实体名称 | 示例 | 简体占位符 | 繁体占位符 |
|------|----------|------|-----------|-----------|
| 中文姓名 | PERSON | 张伟 | `<姓名>` | `<姓名>` |
| 手机号 | CN_PHONE_NUMBER | 13812345678 | `<手机号>` | `<手機號>` |
| 身份证号 | CN_ID_CARD | 110101199001011234 | `<身份证号>` | `<身分證字號>` |
| 银行卡号 | CN_BANK_CARD | 6222021234567890123 | `<银行卡号>` | `<銀行卡號>` |
| 护照号 | CN_PASSPORT | E12345678 | `<护照号>` | `<護照號>` |
| 统一社会信用代码 | CN_SOCIAL_CREDIT_CODE | 91110108MA01234567 | `<统一社会信用代码>` | `<統一社會信用代碼>` |
| 车牌号 | CN_LICENSE_PLATE | 京A12345 | `<车牌号>` | `<車牌號>` |
| 邮箱 | EMAIL_ADDRESS | zhang@example.com | `<邮箱>` | `<信箱>` |
| IP地址 | IP_ADDRESS | 192.168.1.1 | `<IP地址>` | `<IP位址>` |
| 香港电话 | HK_PHONE_NUMBER | 91234567 | `<香港电话>` | `<香港電話>` |
| 香港身份证 | HK_ID_CARD | A123456(7) | `<香港身份证>` | `<香港身份證>` |
| 香港英文姓名 | HK_NAME | Wong Yan Yee | `<香港姓名>` | `<香港姓名>` |

---

## API 参考

### Python SDK

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

### Gateway 配置

```yaml
server:
  host: "0.0.0.0"
  port: 8080

models:
  openai:
    base_url: "https://api.openai.com"
    api_key: "${OPENAI_API_KEY}"

auth:
  mode: "config"  # config | client | both

filter:
  enabled: true
  min_score: 0.5
  action: "redact"  # redact | block | log
```

---

## 项目结构

```
/data/guardrails/
├── chinese_pii_recognizers.py  # PII 识别器模块
├── chinese_guardrail.py         # PII 检测主模块
├── chinese_name_recognizer.py   # 中文姓名识别
├── gateway/                     # HTTP 代理网关（新增）
│   ├── main.py                  # FastAPI 应用入口
│   ├── proxy.py                 # 代理核心逻辑
│   ├── stream_handler.py        # SSE 流处理
│   ├── config.py                # 配置管理
│   └── models.py                # Pydantic 模型
├── configs/
│   └── gateway.yaml             # 网关配置文件
├── test_hk_pii.py               # 香港 PII 测试
├── test_gateway.py              # 网关功能测试
├── demo.py                      # 使用示例
├── run_gateway.sh               # 网关启动脚本
├── requirements.txt             # 依赖
└── README.md                    # 本文件
```

---

## License

MIT
