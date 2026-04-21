#!/bin/bash
# Docker 入口脚本 - 支持环境变量传递

set -e

# 使用环境变量或默认值
HOST="${GATEWAY_HOST:-0.0.0.0}"
PORT="${GATEWAY_PORT:-8080}"
WORKERS="${GATEWAY_WORKERS:-4}"
CONFIG="${GATEWAY_CONFIG:-/app/configs/gateway.yaml}"
LOG_LEVEL="${GATEWAY_LOG_LEVEL:-warning}"

echo "======================================"
echo "LLM Guard Gateway (Docker)"
echo "======================================"
echo "Host:    $HOST"
echo "Port:    $PORT"
echo "Workers: $WORKERS"
echo "Config:  $CONFIG"
echo "Log Level: $LOG_LEVEL"
echo "======================================"

# 检查 API Key 环境变量是否设置
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✓ OPENAI_API_KEY 已设置"
fi
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✓ ANTHROPIC_API_KEY 已设置"
fi
if [ -n "$AZURE_OPENAI_KEY" ]; then
    echo "✓ AZURE_OPENAI_KEY 已设置"
fi

echo ""
echo "启动 Gunicorn..."

# 启动 Gunicorn + Uvicorn
exec gunicorn \
    -w "$WORKERS" \
    -k "uvicorn.workers.UvicornWorker" \
    --bind "$HOST:$PORT" \
    --access-logfile "-" \
    --error-logfile "-" \
    --capture-output \
    --enable-stdio-inheritance \
    --log-level "$LOG_LEVEL" \
    "gateway.main:app"
