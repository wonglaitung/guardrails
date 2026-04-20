"""
LLM Guard Gateway 测试脚本

测试网关的基本功能：
- 健康检查
- PII过滤
- 请求转发（模拟）
"""

import json
import sys
import asyncio
from typing import Dict, Any

# 测试PII过滤功能
print("=" * 70)
print("测试 PII 过滤功能")
print("=" * 70)

from chinese_guardrail import mask_pii, scan_pii

test_cases = [
    ("我的手机号是13812345678", "手机号"),
    ("身份证：110101199001011234", "身份证"),
    ("邮箱：test@example.com", "邮箱"),
    ("香港手机号91234567", "香港电话"),
    ("Name: Wong Yan Yee, Phone: 91234567", "英文姓名和电话"),
]

print("\n1. 快速脱敏测试:")
for text, desc in test_cases:
    safe = mask_pii(text)
    print(f"  [{desc}]")
    print(f"    原文: {text}")
    print(f"    脱敏: {safe}")

print("\n2. 详细检测测试:")
text = "联系人：张三，电话：13812345678，邮箱：zhang@test.com"
safe, entities, has_pii = scan_pii(text)
print(f"  原文: {text}")
print(f"  脱敏: {safe}")
print(f"  检测到 {len(entities)} 个实体:")
for e in entities:
    print(f"    - {e.entity_type}: {e.text}")

# 测试配置系统
print("\n" + "=" * 70)
print("测试配置系统")
print("=" * 70)

from gateway.config import load_config, GatewayConfig

config = load_config("./configs/gateway.yaml")
print(f"\n配置加载成功:")
print(f"  服务器: {config.server.host}:{config.server.port}")
print(f"  模型数量: {len(config.models)}")
print(f"  过滤启用: {config.filter.enabled}")
print(f"  过滤动作: {config.filter.action}")

# 测试代理核心（不依赖外部服务）
print("\n" + "=" * 70)
print("测试代理核心 - 请求过滤")
print("=" * 70)

from gateway.proxy import ProxyHandler
from gateway.config import GatewayConfig, ServerConfig, FilterConfig

# 创建一个测试配置
test_config = GatewayConfig(
    server=ServerConfig(host="127.0.0.1", port=9999),
    filter=FilterConfig(enabled=True, min_score=0.5, action="redact"),
    models={}
)

proxy = ProxyHandler(test_config)

# 测试 OpenAI 格式请求
openai_request = {
    "model": "gpt-4",
    "messages": [
        {"role": "user", "content": "我的手机号是13812345678"}
    ],
    "stream": False
}

print("\nOpenAI 格式请求过滤:")
print(f"  原始: {json.dumps(openai_request, ensure_ascii=False)}")
filtered = asyncio.run(proxy.filter_request(openai_request))
print(f"  过滤: {json.dumps(filtered, ensure_ascii=False)}")

# 测试 Claude 格式请求
claude_request = {
    "model": "claude-3",
    "prompt": "联系人：张三，电话：13812345678",
    "max_tokens": 100
}

print("\nClaude 格式请求过滤:")
print(f"  原始: {json.dumps(claude_request, ensure_ascii=False)}")
filtered = asyncio.run(proxy.filter_request(claude_request))
print(f"  过滤: {json.dumps(filtered, ensure_ascii=False)}")

# 测试 SSE 处理
print("\n" + "=" * 70)
print("测试 SSE 流处理")
print("=" * 70)

from gateway.stream_handler import SSEHandler
from chinese_guardrail import UniversalPIIGuardrail

guardrail = UniversalPIIGuardrail()
sse_handler = SSEHandler(guardrail)

# 测试 SSE 行解析
sse_lines = [
    'data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"我的手机号是13812345678"}}]}',
    'data: [DONE]',
]

print("\nSSE 行过滤测试:")
for line in sse_lines:
    print(f"  原始: {line[:60]}...")
    filtered_line = asyncio.run(sse_handler.filter_sse_line(line))
    print(f"  过滤: {filtered_line[:60]}...")

print("\n" + "=" * 70)
print("测试完成!")
print("=" * 70)
print("\n要启动网关服务，请运行:")
print("  uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload")
print("\n或使用配置文件:")
print("  python -m gateway.main --config configs/gateway.yaml")
