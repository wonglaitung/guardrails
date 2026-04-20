#!/bin/bash
# Docker 镜像构建脚本

set -e

# 镜像名称和标签
IMAGE_NAME="llm-guard-gateway"
TAG="${1:-latest}"

echo "======================================"
echo "Building Docker Image"
echo "======================================"
echo "Image: ${IMAGE_NAME}:${TAG}"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# 构建镜像
docker build \
    --tag "${IMAGE_NAME}:${TAG}" \
    --tag "${IMAGE_NAME}:latest" \
    --file Dockerfile \
    .

echo ""
echo "======================================"
echo "Build Complete!"
echo "======================================"
echo ""
echo "Image: ${IMAGE_NAME}:${TAG}"
echo ""
echo "Run with:"
echo "  ./docker-run.sh"
echo ""
echo "Or directly:"
echo "  docker run -d -p 8080:8080 --name llm-guard-gateway ${IMAGE_NAME}:${TAG}"
