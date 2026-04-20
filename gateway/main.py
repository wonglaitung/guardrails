"""
LLM Guard Gateway - FastAPI主应用

提供HTTP代理服务，支持：
- OpenAI API格式 (/v1/chat/completions)
- Claude API格式 (/v1/messages)
- SSE流式响应
- PII内容过滤
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import load_config, GatewayConfig
from .proxy import ProxyHandler
from .models import HealthResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 全局配置和处理器
config: Optional[GatewayConfig] = None
proxy: Optional[ProxyHandler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global config, proxy

    # 启动时加载配置
    config_path = None
    for arg in sys.argv:
        if arg.startswith("--config"):
            config_path = arg.split("=", 1)[1] if "=" in arg else None

    config = load_config(config_path)
    proxy = ProxyHandler(config)

    logger.info(f"Gateway started on {config.server.host}:{config.server.port}")
    logger.info(f"Available models: {list(config.models.keys())}")
    logger.info(f"Filter enabled: {config.filter.enabled}")

    yield

    # 关闭时清理
    if proxy:
        await proxy.close()
    logger.info("Gateway stopped")


# 创建FastAPI应用
app = FastAPI(
    title="LLM Guard Gateway",
    description="大模型内容过滤转发网关 - 支持OpenAI/Claude API格式",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="ok",
        models=list(config.models.keys()) if config else []
    )


@app.get("/v1/models")
async def list_models():
    """列出可用模型"""
    if not config:
        raise HTTPException(status_code=503, detail="Service not ready")

    models = []
    for key, model_config in config.models.items():
        models.append({
            "id": key,
            "object": "model",
            "owned_by": "gateway",
        })

    return {
        "object": "list",
        "data": models
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI格式的聊天完成接口

    支持流式和非流式响应。
    """
    if not proxy:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # 获取请求头
    headers = dict(request.headers)

    # 过滤请求中的PII
    filtered_body = await proxy.filter_request(body)

    # 检查是否是流式请求
    is_stream = filtered_body.get("stream", False)

    if is_stream:
        return StreamingResponse(
            proxy.stream_forward(filtered_body, headers),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        try:
            response = await proxy.forward(filtered_body, headers)
            return JSONResponse(content=response)
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


@app.post("/v1/messages")
async def claude_messages(request: Request):
    """
    Claude格式的聊天接口

    支持流式和非流式响应。
    """
    if not proxy:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    headers = dict(request.headers)
    filtered_body = await proxy.filter_request(body)
    is_stream = filtered_body.get("stream", False)

    if is_stream:
        return StreamingResponse(
            proxy.stream_forward(filtered_body, headers),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        try:
            response = await proxy.forward(filtered_body, headers)
            return JSONResponse(content=response)
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


@app.post("/v1/completions")
async def completions(request: Request):
    """
    OpenAI格式的文本完成接口（旧版）
    """
    if not proxy:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    headers = dict(request.headers)
    filtered_body = await proxy.filter_request(body)
    is_stream = filtered_body.get("stream", False)

    if is_stream:
        return StreamingResponse(
            proxy.stream_forward(filtered_body, headers),
            media_type="text/event-stream"
        )
    else:
        try:
            response = await proxy.forward(filtered_body, headers)
            return JSONResponse(content=response)
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_error",
            }
        }
    )


def main():
    """入口函数"""
    import uvicorn

    config_path = None
    host = "0.0.0.0"
    port = 8080

    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]
        elif arg.startswith("--host"):
            host = arg.split("=", 1)[1] if "=" in arg else host
        elif arg.startswith("--port"):
            port = int(arg.split("=", 1)[1]) if "=" in arg else port

    # 加载配置
    global config
    config = load_config(config_path)

    # 使用配置中的主机和端口
    host = config.server.host
    port = config.server.port

    uvicorn.run(
        "gateway.main:app",
        host=host,
        port=port,
        workers=config.server.workers,
        log_level=config.logging.level,
    )


if __name__ == "__main__":
    main()
