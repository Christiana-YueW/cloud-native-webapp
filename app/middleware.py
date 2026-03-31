"""
Middleware for automatic API logging and metrics collection.
"""
import logging
import re
import time
import uuid as uuid_lib

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import increment_counter, send_timing

logger = logging.getLogger("csye6225")

UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


class LoggingMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        request_id = str(uuid_lib.uuid4())

        method = request.method.upper()
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        logger.info("request_started", extra={
            "request_id": request_id,
            "method":     method,
            "path":       path,
            "client_ip":  client_ip,
        })

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            self._send_metrics(method, path, duration_ms)
            logger.exception("request_failed", extra={
                "request_id":  request_id,
                "method":      method,
                "path":        path,
                "duration_ms": round(duration_ms, 2),
            })
            raise

        duration_ms = (time.time() - start_time) * 1000
        self._send_metrics(method, path, duration_ms)

        logger.info("request_completed", extra={
            "request_id":  request_id,
            "method":      method,
            "path":        path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        })

        response.headers["X-Request-ID"] = request_id
        return response

    def _send_metrics(self, method: str, path: str, duration_ms: float) -> None:
        metric_path = path.strip("/").replace("/", ".").replace("-", "_")
        if not metric_path:
            metric_path = "root"
        metric_path = UUID_PATTERN.sub("id", metric_path)
        method_part = method.lower()
        increment_counter(f"api.{method_part}.{metric_path}.count")
        send_timing(f"api.{method_part}.{metric_path}.duration", duration_ms)