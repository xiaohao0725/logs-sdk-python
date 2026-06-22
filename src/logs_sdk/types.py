"""SDK 核心类型定义 — 与 Go/Node.js SDK 完全对齐"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
import json, uuid, time, socket, os, re

@dataclass
class LogConfig:
    endpoint: str
    api_key: str
    api_secret: str
    project_slug: str
    environment: str = "production"
    service_name: str = ""
    buffer_size: int = 1000
    flush_interval: int = 5
    max_retries: int = 3
    max_body_size: int = 4096
    max_stack_size: int = 8192

@dataclass
class LogEntry:
    uuid: str = ""
    uid: int = 0
    timestamp: str = ""
    duration_ms: int = 0
    project_slug: str = ""
    environment: str = ""
    service_name: str = ""
    host: str = ""
    process_id: str = ""
    method: str = ""
    scheme: str = ""
    full_url: str = ""
    host_header: str = ""
    path: str = ""
    query_string: str = ""
    origin: str = ""
    request_headers: str = "{}"
    request_body: str = ""
    request_body_size: int = 0
    content_type: str = ""
    status_code: int = 0
    response_headers: str = "{}"
    response_body: str = ""
    response_body_size: int = 0
    client_ip: str = ""
    client_ip_chain: str = ""
    client_type: str = "other"
    client_port: int = 0
    client_country: str = ""
    client_province: str = ""
    client_city: str = ""
    client_isp: str = ""
    user_agent: str = ""
    device_type: str = ""
    browser: str = ""
    browser_version: str = ""
    os_name: str = ""
    os_version: str = ""
    tls_version: str = ""
    tls_cipher: str = ""
    proto: str = ""
    api_version: str = ""
    referer: str = ""
    upstream_status: int = 0
    latency_breakdown: str = "{}"
    request_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: str = ""
    user_id: str = ""
    session_id: str = ""
    is_error: bool = False
    error_message: str = ""
    error_type: str = ""
    error_stack: str = ""
    panic_location: str = ""
    tags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        # Go 服务端期望 tags 为 JSON 对象（map[string]interface{}），
        # 写入 ClickHouse 时服务端自行序列化为字符串
        d = asdict(self)
        d["tags"] = self.tags if self.tags else {}
        return d

def new_uuid() -> str:
    """生成 UUID v7，32 位十六进制无连字符"""
    return uuid.uuid4().hex  # Python uuid4 无原生 v7

def detect_client_type(ua: str, headers: dict) -> str:
    """根据 User-Agent 和请求头识别客户端类型"""
    ct = headers.get("x-client-type", "")
    if ct: return ct
    ua_lower = ua.lower()
    if "micromessenger" in ua_lower or "miniprogram" in ua_lower: return "miniprogram"
    if headers.get("x-caller-service"): return "server"
    ref = headers.get("referer", "") or headers.get("origin", "")
    if ref and any(b in ua_lower for b in ("mozilla", "chrome", "safari", "firefox")): return "web"
    return "other"

def detect_origin(headers: dict, ua: str) -> str:
    ct = detect_client_type(ua, headers)
    if ct == "web": return headers.get("referer", "") or headers.get("origin", "")
    if ct == "miniprogram": return f"miniprogram:{headers.get('x-miniprogram-appid','')}{headers.get('x-miniprogram-path','')}"
    if ct == "app": return f"app:{headers.get('x-app-name','')}/{headers.get('x-app-version','')}/{headers.get('x-app-scene','')}"
    if ct == "server": return f"server:{headers.get('x-caller-service','')}/{headers.get('x-caller-version','')}"
    return "unknown"

def sanitize_headers(headers: dict) -> str:
    safe = {}
    for k, v in headers.items():
        v = v[0] if isinstance(v, list) else str(v) if v else ""
        if k.lower() in ("authorization", "cookie", "set-cookie"):
            safe[k] = v[:15] + "..." if len(v) > 20 else "***"
        else:
            safe[k] = v
    return json.dumps(safe)

def extract_api_version(path: str) -> str:
    m = re.match(r"/api/(v\d+)(/|$)", path)
    return m.group(1) if m else ""
