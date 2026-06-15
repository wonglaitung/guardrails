# 10 - 测试与示例

## 概述

本文档介绍项目的测试策略和常见使用示例。

## 测试文件

| 文件 | 用途 |
|------|------|
| `test_hk_pii.py` | 香港 PII 识别器测试 |
| `test_gateway.py` | 网关功能测试 |
| `chinese_guardrail.py` | 内置自测（运行时执行） |
| `demo.py` | 完整演示脚本 |

## Layer 1 测试

### 基础功能测试

```python
# chinese_guardrail.py 内置测试
python chinese_guardrail.py
```

输出：
```
======================================================================
通用 PII Guardrail 测试（自动检测中英文）
======================================================================

[简体中文] 原文: 我的名字叫张伟，手机号是13812345678
检测到 2 个 PII 实体:
  • PERSON: '张伟' (置信度: 0.85)
  • CN_PHONE_NUMBER: '13812345678' (置信度: 0.95)
脱敏: 我的名字叫<姓名>，手机号是<手机号>
```

### 手机号测试

```python
def test_phone_number():
    guardrail = ChinesePIIGuardrail()
    
    # 标准格式
    entities = guardrail.detect("手机号13812345678")
    assert len(entities) == 1
    assert entities[0].entity_type == "CN_PHONE_NUMBER"
    assert entities[0].text == "13812345678"
    
    # 多个手机号
    entities = guardrail.detect("手机13811112222和13987654321")
    assert len(entities) == 2
```

### 身份证测试

```python
def test_id_card():
    guardrail = ChinesePIIGuardrail()
    
    # 18位身份证
    entities = guardrail.detect("身份证号110101199001011234")
    assert len(entities) == 1
    assert entities[0].entity_type == "CN_ID_CARD"
    
    # 15位身份证（旧版）
    entities = guardrail.detect("旧身份证123456789012345")
    assert len(entities) == 1
```

### 银行卡测试

```python
def test_bank_card():
    guardrail = ChinesePIIGuardrail()
    
    # 银行卡号（需要上下文）
    entities = guardrail.detect("银行卡号6222021234567890123")
    assert len(entities) == 1
    assert entities[0].entity_type == "CN_BANK_CARD"
```

### 香港身份证测试

```python
# test_hk_pii.py
python test_hk_pii.py
```

```python
def test_hk_id_card():
    guardrail = UniversalPIIGuardrail()
    
    # 单字母格式
    entities = guardrail.detect("香港身份证A123456(7)")
    assert len(entities) == 1
    assert entities[0].entity_type == "HK_ID_CARD"
    
    # 双字母格式
    entities = guardrail.detect("身份证AB123456(A)")
    assert len(entities) == 1
```

### 香港姓名测试

```python
def test_hk_name():
    guardrail = UniversalPIIGuardrail()
    
    # 有上下文
    entities = guardrail.detect("客户姓名：Wong Yan Yee")
    assert len(entities) == 1
    assert entities[0].entity_type == "HK_NAME"
    
    # 香港常见姓氏
    entities = guardrail.detect("联系人Chan Tai Man")
    assert entities[0].text == "Chan Tai Man"
```

## 语言检测测试

```python
def test_script_detection():
    guardrail = UniversalPIIGuardrail()
    
    # 简体
    assert guardrail._detect_script("我的手机号是138xxx") == "simplified"
    
    # 繁体
    assert guardrail._detect_script("手機號是138xxx") == "traditional"
    
    # 英文
    assert guardrail._detect_script("My phone is 138xxx") == "english"
    
    # 混合
    result = guardrail._detect_script("Contact: 张三")
    assert result in ["simplified", "english"]
```

## Gateway 测试

### 启动测试

```bash
# 启动网关（开发模式）
./run_gateway.sh -d

# 或
uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload
```

### 基础请求测试

```bash
# 测试健康检查
curl http://localhost:8080/health

# 测试模型列表
curl http://localhost:8080/v1/models
```

### PII 过滤测试

```bash
# 手机号过滤
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "我的手机号是13812345678"}
    ]
  }'

# 请求会被过滤，上游服务收到：
# {"role": "user", "content": "我的手机号是<手机号>"}
```

### 流式响应测试

```bash
# 流式请求
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "stream": true
  }'
```

### 网关功能测试

```python
# test_gateway.py
python test_gateway.py
```

## Judge 测试（Layer 2）

### Judge 服务启动

```bash
# 启动 Qwen3Guard 服务
python -m vllm.entrypoints.openai.api_server \
  --model ./models/Qwen3Guard-8B-Stream \
  --host 0.0.0.0 \
  --port 8001
```

### Judge 功能测试

```python
import asyncio
from gateway.judge import ComplianceJudge
from gateway.config import JudgeConfig

async def test_judge():
    config = JudgeConfig(
        enabled=True,
        endpoint="http://localhost:8001/v1/chat/completions",
        model="Qwen3Guard-8B-Stream",
    )
    
    judge = ComplianceJudge(config)
    
    # 测试安全内容
    result = await judge.judge("你好，请帮我写一个故事")
    assert result.is_safe
    
    # 测试快速检测
    score = await judge.quick_check("这是一段测试文本")
    assert 0.0 <= score <= 1.0
    
    await judge.close()

asyncio.run(test_judge())
```

### 流式拦截测试

```python
async def test_stream_intercept():
    # 模拟恶意流
    malicious_stream = generate_malicious_content()
    
    interceptor = StreamInterceptor(judge, config)
    
    intercepted = False
    async for line in interceptor.intercept(malicious_stream):
        if "[内容安全警告" in line:
            intercepted = True
    
    assert intercepted
```

## 完整演示

```bash
# 运行完整演示
python demo.py
```

演示内容：
1. 简体中文 PII 检测
2. 繁体中文 PII 检测
3. 英文 PII 检测
4. 中英混合文本
5. 多 PII 组合
6. 自定义占位符

## 使用示例

### 基础脱敏

```python
from chinese_guardrail import mask_pii

# 简体
safe_text = mask_pii("我的手机是13812345678")
print(safe_text)  # 我的手机是<手机号>

# 繁体
safe_text = mask_pii("手機號是13812345678")
print(safe_text)  # 手機號是<手機號>

# 英文
safe_text = mask_pii("My phone is 13812345678", lang="en")
print(safe_text)  # My phone is <PHONE>
```

### 完整扫描

```python
from chinese_guardrail import scan_pii

text = "联系人：张三，电话：13912345678，邮箱：zhang@test.com"
safe_text, entities, has_pii = scan_pii(text)

print(f"脱敏后: {safe_text}")
print(f"发现 {len(entities)} 个 PII:")
for e in entities:
    print(f"  - {e.entity_type}: {e.text} (置信度: {e.score:.2f}")
```

### 自定义占位符

```python
from chinese_guardrail import ChinesePIIGuardrail

guardrail = ChinesePIIGuardrail(
    placeholders={
        "CN_PHONE_NUMBER": "[已脱敏]",
        "CN_ID_CARD": "***",
    }
)

safe_text = guardrail.redact("手机13812345678，身份证110101199001011234")
print(safe_text)  # 手机[已脱敏]，身份证***
```

### 批量处理

```python
from chinese_guardrail import UniversalPIIGuardrail

guardrail = UniversalPIIGuardrail()

texts = [
    "手机号13812345678",
    "身份证110101199001011234",
    "邮箱test@example.com",
]

for text in texts:
    safe_text, entities, has_pii = guardrail.check(text)
    if has_pii:
        print(f"原文: {text}")
        print(f"脱敏: {safe_text}")
```

### 集成到应用

```python
# FastAPI 集成
from fastapi import FastAPI
from chinese_guardrail import mask_pii

app = FastAPI()

@app.post("/submit")
async def submit(data: dict):
    # 自动脱敏用户输入
    safe_content = mask_pii(data["content"])
    
    # 存储安全内容
    save_to_db(safe_content)
    
    return {"status": "ok"}
```

### 验证输入

```python
from chinese_guardrail import ChinesePIIGuardrail

guardrail = ChinesePIIGuardrail()

def validate_user_input(text: str) -> tuple[bool, str]:
    """验证用户输入是否安全"""
    is_safe = guardrail.validate(text)
    
    if not is_safe:
        safe_text = guardrail.redact(text)
        return False, f"输入包含敏感信息，已自动脱敏: {safe_text}"
    
    return True, text

# 使用
is_valid, message = validate_user_input("手机13812345678")
if not is_valid:
    print(message)
```

## 性能测试

### 基准测试

```python
import time
from chinese_guardrail import UniversalPIIGuardrail

guardrail = UniversalPIIGuardrail()

# 测试文本
text = "手机13812345678，身份证110101199001011234，邮箱test@example.com"

# 单次检测
start = time.time()
result = guardrail.check(text)
elapsed = time.time() - start
print(f"单次检测: {elapsed*1000:.2f}ms")

# 批量检测
texts = [text] * 1000
start = time.time()
for t in texts:
    guardrail.check(t)
elapsed = time.time() - start
print(f"1000次检测: {elapsed:.2f}s ({elapsed*1000:.2f}ms/次)")
```

### 预期性能

| 操作 | 预期延迟 |
|------|----------|
| 单次检测 | < 1ms |
| 脱敏处理 | < 2ms |
| 完整检查 | < 3ms |
| Judge 检测 | 200-500ms (quick) / 500-2000ms (完整) |