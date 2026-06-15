# Guardrails 项目设计文档

> 中文 PII 检测与脱敏护栏系统

## 目录

- [01-overview.md](./01-overview.md) - 项目概述与架构总览
- [02-layer1-pii.md](./02-layer1-pii.md) - Layer 1: PII 规则检测层
- [03-layer2-judge.md](./03-layer2-judge.md) - Layer 2: LLM 实时裁判层
- [04-gateway.md](./04-gateway.md) - HTTP 代理网关
- [05-configuration.md](./05-configuration.md) - 配置系统
- [06-streaming.md](./06-streaming.md) - 流式处理与拦截
- [07-i18n.md](./07-i18n.md) - 多语言支持（简繁体）
- [08-deployment.md](./08-deployment.md) - 部署指南
- [09-api-reference.md](./09-api-reference.md) - API 参考

## 项目定位

构建一个**双层护栏系统**，为大模型应用提供内容安全保护：

```
请求 → Layer 1 (PII规则检测) → Layer 2 (LLM Judge) → 上游服务
              ↓                        ↓
           PII脱敏              风险检测/流式拦截
```

### 核心理念

```
Guardrails = Layer 1 (规则) + Layer 2 (语义)
```

- **Layer 1**: 精准、快速（<1ms），适用于格式化数据（手机、身份证、银行卡）
- **Layer 2**: 语义理解、意图判断，适用于隐晦攻击、语义操纵

### 与现有方案的区别

| 项目 | 定位 | 检测方式 | 延迟 |
|------|------|----------|------|
| Microsoft Presidio | 通用 PII 检测 | 规则 + NER | 低 |
| LlamaGuard | 内容安全 | LLM 判断 | 高 |
| **本 Guardrails** | 双层防护 | 规则 + LLM | 可选 |

## 快速预览

### 最简使用示例

```python
from chinese_guardrail import mask_pii

# 自动检测语言并脱敏
safe_text = mask_pii("我的手机号是13812345678")
# 输出: "我的手机号是<手机号>"

safe_text = mask_pii("手機號是13812345678")
# 输出: "手機號是<手機號>"
```

### 网关代理使用

```python
import httpx

# 通过网关调用 OpenAI API
response = httpx.post(
    "http://localhost:8080/v1/chat/completions",
    json={
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "我的身份证号是110101199001011234"}
        ]
    }
)

# 请求会被自动过滤，PII 不会发送到上游服务
```

### 启用 Layer 2 Judge

```yaml
# configs/gateway.yaml
judge:
  enabled: true
  endpoint: "http://localhost:8001/v1/chat/completions"
  model: "Qwen3Guard-8B-Stream"
  timeout: 5.0
```

## 设计原则

1. **双层防护**: Layer 1 精准快速 + Layer 2 语义理解
2. **多语言支持**: 简体中文、繁体中文、英文及混合文本
3. **透明代理**: 支持 OpenAI/Claude API 格式，无缝集成
4. **流式优先**: SSE 流式转发，实时 PII 过滤
5. **可选依赖**: Judge 缓存、流式拦截等功能可按需启用
