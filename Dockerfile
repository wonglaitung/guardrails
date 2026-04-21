# LLM Guard Gateway Dockerfile
# 生产就绪配置：使用 Gunicorn + Uvicorn worker

# ========== 阶段一：构建环境 ==========
FROM python:3.11-slim AS builder

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt .

# 安装依赖到虚拟环境（减小镜像体积）
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn uvicorn[standard] httpx[http2]

# 下载 spaCy 模型（中文 + 轻量级英文，避免运行时下载大模型）
RUN python -m spacy download zh_core_web_sm && \
    python -m spacy download en_core_web_sm

# ========== 阶段二：运行环境 ==========
FROM python:3.11-slim AS runtime

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r gateway && useradd -r -g gateway gateway

# 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 设置工作目录
WORKDIR /app

# 创建必要的目录
RUN mkdir -p /app/configs /app/logs && \
    chown -R gateway:gateway /app

# 复制应用代码
COPY --chown=gateway:gateway gateway/ ./gateway/
COPY --chown=gateway:gateway chinese_guardrail.py .
COPY --chown=gateway:gateway chinese_pii_recognizers.py .
COPY --chown=gateway:gateway chinese_name_recognizer.py .

# 复制默认配置文件
COPY --chown=gateway:gateway configs/gateway.yaml ./configs/

# 切换到非 root 用户
USER gateway

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 复制启动脚本
COPY --chown=gateway:gateway docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 设置环境变量默认值
ENV GATEWAY_WORKERS=4 \
    GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8080 \
    GATEWAY_CONFIG=/app/configs/gateway.yaml

# 启动命令：使用入口脚本支持环境变量
ENTRYPOINT ["docker-entrypoint.sh"]
