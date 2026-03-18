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

# UUID pattern for normalizing path parameters
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

        logger.info(
            f"request_started request_id={request_id} method={method} path={path} client_ip={client_ip}"
        )

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            self._send_metrics(method, path, duration_ms)

            logger.exception(
                f"request_failed request_id={request_id} method={method} path={path} duration_ms={duration_ms:.2f}"
            )
            raise

        duration_ms = (time.time() - start_time) * 1000
        self._send_metrics(method, path, duration_ms)

        logger.info(
            f"request_completed request_id={request_id} method={method} path={path} "
            f"status_code={status_code} duration_ms={duration_ms:.2f}"
        )

        response.headers["X-Request-ID"] = request_id
        return response

    def _send_metrics(self, method: str, path: str, duration_ms: float) -> None:
        # Normalize path: /v1/courses/{uuid} -> v1.courses.id
        metric_path = path.strip("/").replace("/", ".").replace("-", "_")
        
        if not metric_path:
            metric_path = "root"
        
        # Replace UUIDs with 'id'
        metric_path = UUID_PATTERN.sub("id", metric_path)
        
        method_part = method.lower()

        increment_counter(f"api.{method_part}.{metric_path}.count")
        send_timing(f"api.{method_part}.{metric_path}.duration", duration_ms)