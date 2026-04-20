"""
中间件模块

提供认证、日志、限流等中间件功能。
"""

import time
import logging
from typing import Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 记录请求信息
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"{request.method} {request.url.path} - {client_host}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )

            # 添加响应头
            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {e} - "
                f"Time: {process_time:.3f}s"
            )
            raise


class FilterMiddleware(BaseHTTPMiddleware):
    """PII过滤中间件"""

    def __init__(self, app: ASGIApp, whitelist_paths: Optional[list] = None):
        super().__init__(app)
        self.whitelist_paths = set(whitelist_paths or ["/health", "/metrics"])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 白名单路径跳过检查
        if request.url.path in self.whitelist_paths:
            return await call_next(request)

        # 这里可以添加全局的PII检查逻辑
        # 目前主要在路由处理中进行

        return await call_next(request)
