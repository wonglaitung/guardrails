"""
LLM Guard Gateway - FastAPI主应用

提供HTTP代理服务，支持：
- OpenAI API格式 (/v1/chat/completions)
- Claude API格式 (/v1/messages)
- SSE流式响应
- PII内容过滤
- Layer 2 实时裁判（Judge）
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
from .exceptions import (
    ContentRiskException,
    JudgeTimeoutException,
    JudgeUnavailableException,
    StreamInterruptException,
)

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

    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"
    x_forwarded_for = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP")
    client_info = x_forwarded_for or client_ip

    # 过滤请求中的PII
    filtered_body = await proxy.filter_request(body, client_info)

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


@app.exception_handler(ContentRiskException)
async def content_risk_exception_handler(request: Request, exc: ContentRiskException):
    """内容风险异常处理 - 返回详细的风险信息"""
    logger.warning(f"Content risk detected: {exc.result.risk_level} - {exc.result.reason}")

    # 根据风险等级决定 HTTP 状态码
    status_code = 400 if exc.result.risk_level in ["low", "medium"] else 403

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": "content_policy_violation",
                "message": "您的内容触发安全策略限制，请修改后重试。",
                "details": {
                    "risk_level": exc.result.risk_level,
                    "risk_categories": exc.result.risk_categories,
                    "confidence": round(exc.result.confidence, 2),
                    "reason": exc.result.reason,
                },
                "suggestion": "请检查内容是否包含敏感信息或违规表述，修改后重新提交。"
            }
        }
    )


@app.exception_handler(JudgeTimeoutException)
async def judge_timeout_exception_handler(request: Request, exc: JudgeTimeoutException):
    """Judge 服务超时异常处理"""
    logger.warning(f"Judge timeout: {exc.endpoint}")

    return JSONResponse(
        status_code=504,
        content={
            "error": {
                "type": "judge_timeout",
                "message": "安全审核服务响应超时，请稍后重试。",
                "details": {
                    "timeout_seconds": exc.timeout,
                    "endpoint": exc.endpoint,
                }
            }
        }
    )


@app.exception_handler(JudgeUnavailableException)
async def judge_unavailable_exception_handler(request: Request, exc: JudgeUnavailableException):
    """Judge 服务不可用异常处理"""
    logger.error(f"Judge unavailable: {exc.endpoint} - {exc.reason}")

    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "type": "judge_unavailable",
                "message": "安全审核服务暂时不可用，请稍后重试。",
                "details": {
                    "endpoint": exc.endpoint,
                    "reason": exc.reason,
                }
            }
        }
    )


@app.exception_handler(StreamInterruptException)
async def stream_interrupt_exception_handler(request: Request, exc: StreamInterruptException):
    """流式输出中断异常处理"""
    logger.warning(f"Stream interrupted: {exc.reason}")

    return JSONResponse(
        status_code=200,  # 流式响应已部分发送，返回 200
        content={
            "error": {
                "type": "stream_interrupted",
                "message": "输出内容触发安全策略，已中断。",
                "details": {
                    "reason": exc.reason,
                    "partial_content_length": len(exc.partial_content),
                }
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
