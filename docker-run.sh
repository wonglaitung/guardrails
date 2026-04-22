#!/bin/bash
# Docker 容器运行脚本

set -e

# 配置
IMAGE_NAME="llm-guard-gateway"
CONTAINER_NAME="llm-guard-gateway"
PORT="${GATEWAY_PORT:-8080}"
CONFIG_FILE="${GATEWAY_CONFIG:-./configs/gateway.yaml}"

echo "======================================"
echo "Starting LLM Guard Gateway Container"
echo "======================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# 检查镜像是否存在
if ! docker image inspect "${IMAGE_NAME}:latest" &> /dev/null; then
    echo "Image not found. Building first..."
    ./docker-build.sh
fi

# 停止并删除已存在的容器
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping existing container..."
    docker stop "${CONTAINER_NAME}" &> /dev/null || true
    docker rm "${CONTAINER_NAME}" &> /dev/null || true
fi

# 检查配置文件
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Warning: Config file not found: ${CONFIG_FILE}"
    echo "Using default config in container"
    CONFIG_VOLUME=""
else
    echo "Using config: ${CONFIG_FILE}"
    CONFIG_VOLUME="-v $(pwd)/${CONFIG_FILE}:/app/configs/gateway.yaml"
fi

# 构建环境变量参数
# 从配置文件中自动提取 ${VAR_NAME} 格式的环境变量名
ENV_VARS=""
if [ -f "${CONFIG_FILE}" ]; then
    # 提取所有 ${VAR_NAME} 格式的变量名
    VAR_NAMES=$(grep -oE '\$\{[A-Za-z_][A-Za-z0-9_]*\}' "${CONFIG_FILE}" | sed 's/[${}]//g' | sort -u)
    for var_name in $VAR_NAMES; do
        var_value="${!var_name}"
        if [ -n "$var_value" ]; then
            ENV_VARS="${ENV_VARS} -e ${var_name}=${var_value}"
        fi
    done
fi

echo ""
echo "Starting container..."
echo "  Port: ${PORT}:8080"
echo "  Name: ${CONTAINER_NAME}"
echo ""

# 运行容器
docker run -d \
    --name "${CONTAINER_NAME}" \
    -p "${PORT}:8080" \
    ${CONFIG_VOLUME} \
    ${ENV_VARS} \
    --restart unless-stopped \
    --health-interval 30s \
    --health-timeout 10s \
    --health-retries 3 \
    "${IMAGE_NAME}:latest"

echo "Container started!"
echo ""
echo "Health check:"
sleep 2
if curl -s http://localhost:${PORT}/health > /dev/null; then
    echo "✓ Gateway is healthy"
    echo ""
    echo "API endpoint: http://localhost:${PORT}"
    echo "Health check: http://localhost:${PORT}/health"
else
    echo "⚠ Waiting for gateway to be ready..."
    echo "Check logs with: docker logs ${CONTAINER_NAME}"
fi

echo ""
echo "Useful commands:"
echo "  View logs:    docker logs -f ${CONTAINER_NAME}"
echo "  Stop:         docker stop ${CONTAINER_NAME}"
echo "  Restart:      docker restart ${CONTAINER_NAME}"
echo "  Remove:       docker rm -f ${CONTAINER_NAME}"
