"""FastAPI/Starlette/Flask 中间件 — 自动采集所有 HTTP 请求日志"""
import time, traceback, sys, json
from .types import LogEntry, new_uuid, detect_client_type, detect_origin, sanitize_headers, extract_api_version


class FastAPIMiddleware:
    """Starlette BaseHTTPMiddleware 实现，兼容 FastAPI"""

    def __init__(self, sdk):
        self.sdk = sdk

    async def dispatch(self, request, call_next):
        entry = LogEntry()
        entry.uuid = new_uuid()
        entry.request_id = entry.uuid[:8]
        entry.trace_id = entry.uuid
        entry.span_id = entry.uuid
        start = time.time()

        # 读取请求体（缓存以支持多次读取）
        body_bytes = b""
        try:
            body_bytes = await request.body()
        except Exception:
            pass

        # 请求信息
        headers = dict(request.headers)
        entry.method = request.method
        entry.scheme = request.url.scheme
        entry.full_url = str(request.url)
        entry.host_header = request.headers.get("host", "")
        entry.path = request.url.path
        entry.query_string = request.url.query
        entry.content_type = request.headers.get("content-type", "")
        entry.user_agent = request.headers.get("user-agent", "")
        entry.client_ip = headers.get("x-forwarded-for", request.client.host if request.client else "")
        entry.client_ip_chain = headers.get("x-forwarded-for", "")
        entry.client_type = detect_client_type(entry.user_agent, headers)
        entry.origin = detect_origin(headers, entry.user_agent)
        entry.request_headers = sanitize_headers(headers)
        entry.request_body = body_bytes[:self.sdk.config.max_body_size].decode("utf-8", errors="replace")
        entry.request_body_size = len(body_bytes)
        entry.referer = request.headers.get("referer", "")
        entry.trace_id = headers.get("x-trace-id", entry.uuid)
        entry.parent_span_id = headers.get("x-parent-span-id", "")
        entry.user_id = headers.get("x-user-id", "")
        entry.session_id = headers.get("x-session-id", "")
        entry.api_version = extract_api_version(entry.path)
        entry.proto = request.scope.get("http_version", "1.1")
        entry.tls_version = getattr(request.scope.get("transport"), "get_extra_info", lambda x: "")(f"tls_version") or ""

        # 执行业务
        try:
            response = await call_next(request)
        except Exception as e:
            entry.is_error = True
            entry.error_type = "panic"
            entry.error_message = str(e)
            entry.error_stack = traceback.format_exc()
            raise
        finally:
            entry.duration_ms = int((time.time() - start) * 1000)

        # 响应信息
        entry.status_code = getattr(response, "status_code", 200)
        resp_headers = dict(getattr(response, "headers", {}))
        entry.response_headers = sanitize_headers(resp_headers)

        # 捕获响应体
        resp_body = b""
        try:
            if hasattr(response, "body"):
                resp_body = response.body if isinstance(response.body, bytes) else str(response.body).encode("utf-8")
                entry.response_body_size = len(resp_body)
                entry.response_body = resp_body[:self.sdk.config.max_body_size].decode("utf-8", errors="replace")
            else:
                entry.response_body_size = int(resp_headers.get("content-length", 0))
        except Exception:
            entry.response_body_size = int(resp_headers.get("content-length", 0)) if resp_headers.get("content-length") else 0

        if entry.status_code >= 400:
            entry.is_error = True
            entry.error_type = "http_error"
            entry.error_message = entry.response_body
            if entry.status_code >= 500:
                entry.error_stack = traceback.format_stack()

        self.sdk.send(entry)
        return response


class FlaskMiddleware:
    """Flask WSGI 中间件"""

    def __init__(self, sdk):
        self.sdk = sdk

    def __call__(self, environ, start_response):
        entry = LogEntry()
        entry.uuid = new_uuid()
        entry.request_id = entry.uuid[:8]
        entry.trace_id = entry.uuid
        entry.span_id = entry.uuid
        start = time.time()

        entry.method = environ.get("REQUEST_METHOD", "")
        entry.scheme = environ.get("wsgi.url_scheme", "http")
        entry.host_header = environ.get("HTTP_HOST", "")
        entry.path = environ.get("PATH_INFO", "")
        entry.query_string = environ.get("QUERY_STRING", "")
        entry.full_url = f"{entry.scheme}://{entry.host_header}{entry.path}" + (f"?{entry.query_string}" if entry.query_string else "")
        entry.user_agent = environ.get("HTTP_USER_AGENT", "")
        entry.client_ip = environ.get("HTTP_X_FORWARDED_FOR", environ.get("REMOTE_ADDR", ""))
        entry.content_type = environ.get("CONTENT_TYPE", "")

        headers = {k.replace("HTTP_", "").lower().replace("_", "-"): v for k, v in environ.items() if k.startswith("HTTP_")}
        entry.client_type = detect_client_type(entry.user_agent, headers)
        entry.origin = detect_origin(headers, entry.user_agent)
        entry.request_headers = sanitize_headers(headers)
        entry.api_version = extract_api_version(entry.path)

        # 读取请求体
        try:
            body = environ["wsgi.input"].read(self.sdk.config.max_body_size)
            entry.request_body = body.decode("utf-8", errors="replace")
            entry.request_body_size = len(body)
        except Exception:
            pass

        status_code = 200

        def _start_response(status, response_headers, exc_info=None):
            nonlocal status_code
            status_code = int(status.split()[0])
            resp_headers = {k.lower(): v for k, v in response_headers}
            entry.response_headers = sanitize_headers(resp_headers)
            return start_response(status, response_headers, exc_info)

        try:
            response_iter = self.sdk.app(environ, _start_response)
            entry.duration_ms = int((time.time() - start) * 1000)
            entry.status_code = status_code
            if status_code >= 400:
                entry.is_error = True
                entry.error_type = "http_error"
                entry.error_message = entry.response_body
            self.sdk.send(entry)
            return response_iter
        except Exception as e:
            entry.is_error = True
            entry.error_type = "panic"
            entry.error_message = str(e)
            entry.error_stack = traceback.format_exc()
            entry.duration_ms = int((time.time() - start) * 1000)
            self.sdk.send(entry)
            raise
