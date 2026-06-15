# 08 - 部署指南

## 概述

本文档介绍 Guardrails Gateway 的部署方式，包括开发环境、生产环境和 Docker 部署。

## 系统要求

### 基础要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.9+ |
| pip | 21.0+ |
| 内存 | 最低 512MB，推荐 1GB+ |
| CPU | 1 核+ |

### 可选依赖

| 组件 | 用途 |
|------|------|
| spaCy `zh_core_web_sm` | 中文 NLP（可选） |
| `cachetools` | Judge 缓存（推荐） |

## 安装步骤

### 1. 安装依赖

```bash
# 克隆项目
git clone <repo-url>
cd guardrails

# 安装 Python 依赖
pip install -r requirements.txt

# 安装网关额外依赖
pip install fastapi uvicorn httpx pydantic pyyaml python-dotenv python-multipart

# 安装可选依赖
pip install cachetools  # Judge 缓存
```

### 2. 安装 spaCy 模型（可选）

```bash
# 中文模型（可选，项目未使用）
python -m spacy download zh_core_web_sm

# 英文模型（Presidio 需要）
python -m spacy download en_core_web_sm
```

### 3. 创建配置文件

```bash
# 创建配置目录
mkdir -p configs

# 复制示例配置
cp configs/gateway.yaml.example configs/gateway.yaml

# 编辑配置
vim configs/gateway.yaml
```

### 4. 设置环境变量

```bash
# 创建 .env 文件
cat > .env << EOF
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-xxx-xxx
EOF

# 加载环境变量
source .env
```

## 开发环境部署

### 直接运行

```bash
# 使用 uvicorn 开发模式（自动重载）
uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload

# 或使用启动脚本
./run_gateway.sh -d
```

### 开发配置

```yaml
# configs/gateway.yaml
server:
  host: "0.0.0.0"
  port: 8080
  workers: 1

logging:
  level: "debug"

filter:
  min_score: 0.4  # 开发环境更宽松

judge:
  enabled: false  # 开发时可禁用
```

## 生产环境部署

### Uvicorn + Gunicorn

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动（多进程）
gunicorn gateway.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080 \
  --timeout 120 \
  --keep-alive 5
```

### 生产配置

```yaml
# configs/gateway.yaml
server:
  host: "0.0.0.0"
  port: 8080
  workers: 4

logging:
  level: "info"

filter:
  enabled: true
  min_score: 0.6  # 生产环境更严格
  filter_response: false

auth:
  mode: "config"  # 只用配置文件的 API Key

judge:
  enabled: true
  timeout: 3.0
  timeout_action: "pass"  # 高可用场景
```

### Systemd 服务

```ini
# /etc/systemd/system/guardrails.service
[Unit]
Description=Guardrails Gateway
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/guardrails
Environment="PATH=/opt/guardrails/venv/bin"
Environment="GATEWAY_CONFIG=/opt/guardrails/configs/gateway.yaml"
ExecStart=/opt/guardrails/venv/bin/gunicorn gateway.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable guardrails
sudo systemctl start guardrails
```

## Docker 部署

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic pyyaml python-dotenv python-multipart

# 安装 spaCy 模型
RUN python -m spacy download en_core_web_sm

# 复制代码
COPY . .

# 创建非 root 用户
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 构建镜像

```bash
# 构建镜像
docker build -t guardrails:latest .

# 或使用脚本
./docker-build.sh
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  gateway:
    image: guardrails:latest
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GATEWAY_CONFIG=/app/configs/gateway.yaml
    volumes:
      - ./configs:/app/configs:ro
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  # Judge 服务（可选）
  judge:
    image: qwen3guard:latest
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 运行容器

```bash
# 使用脚本
./docker-run.sh

# 或手动运行
docker run -d \
  --name guardrails \
  -p 8080:8080 \
  -e OPENAI_API_KEY=sk-xxx \
  -v $(pwd)/configs:/app/configs:ro \
  guardrails:latest
```

## Nginx 反向代理

### 配置示例

```nginx
# /etc/nginx/sites-available/guardrails
upstream guardrails {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name api.example.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # 代理配置
    location / {
        proxy_pass http://guardrails;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 健康检查
    location /health {
        proxy_pass http://guardrails/health;
        access_log off;
    }
}
```

## Layer 2 Judge 部署

### Qwen3Guard-8B-Stream 部署

```bash
# 下载模型
huggingface-cli download Qwen/Qwen3Guard-8B-Stream --local-dir ./models/Qwen3Guard-8B-Stream

# 启动服务
python -m vllm.entrypoints.openai.api_server \
    --model ./models/Qwen3Guard-8B-Stream \
    --host 0.0.0.0 \
    --port 8001 \
    --gpu-memory-utilization 0.9
```

### 配置 Gateway 连接 Judge

```yaml
judge:
  enabled: true
  endpoint: "http://judge:8001/v1/chat/completions"
  model: "Qwen3Guard-8B-Stream"
  timeout: 5.0
```

## 监控与日志

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8080/health

# 响应
{
  "status": "ok",
  "models": ["gpt-4", "claude-3"]
}
```

### 日志配置

```yaml
logging:
  level: "info"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 日志轮转

```python
# 使用 logging.handlers
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    '/var/log/guardrails/gateway.log',
    maxBytes=100*1024*1024,  # 100MB
    backupCount=10
)
```

## 性能调优

### Worker 数量

```bash
# CPU 核心数
nproc

# 推荐 Worker 数 = CPU 核心数 * 2 + 1
# 例如：4 核 CPU → 9 workers
gunicorn gateway.main:app --workers 9
```

### 内存配置

```yaml
# 限制最大内存
filter:
  min_score: 0.5  # 较低阈值减少处理

judge:
  cache_maxsize: 1000  # 缓存大小
```

### 连接池

```python
# httpx 连接池
self.client = httpx.AsyncClient(
    http2=True,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
    )
)
```

## 安全建议

### 1. 使用 HTTPS

```nginx
# 强制 HTTPS
return 301 https://$server_name$request_uri;
```

### 2. API Key 保护

```yaml
# 不要硬编码 API Key
api_key: "${OPENAI_API_KEY}"  # ✓ 使用环境变量

# 不要提交 .env 文件
# .gitignore
.env
*.secret
```

### 3. 网络隔离

```yaml
# 只监听内网
server:
  host: "127.0.0.1"  # 只接受本地连接
```

### 4. 认证模式

```yaml
auth:
  mode: "config"  # 只用配置文件的 API Key，忽略客户端提供的
```

## 故障排查

### 常见问题

```bash
# 检查端口占用
netstat -tlnp | grep 8080

# 检查日志
tail -f /var/log/guardrails/gateway.log

# 测试连接
curl -v http://localhost:8080/health
```

### 重启服务

```bash
# Systemd
sudo systemctl restart guardrails

# Docker
docker restart guardrails

# 手动
pkill -f uvicorn && uvicorn gateway.main:app --host 0.0.0.0 --port 8080
```