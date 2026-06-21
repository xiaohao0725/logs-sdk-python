"""核心客户端 — 缓冲管理、定时刷新、HTTP 上报、离线缓存"""
import json, time, os, socket, threading, logging
import httpx
from .types import LogConfig, LogEntry, new_uuid
from .buffer import RingBuffer
from .offline import OfflineCache

logger = logging.getLogger("logs-sdk")

class LogSDK:
    def __init__(self, **kwargs):
        self.config = LogConfig(**{k: v for k, v in kwargs.items() if k in LogConfig.__dataclass_fields__})
        self.hostname = socket.gethostname()
        self.pid = str(os.getpid())
        self.offline_cache = OfflineCache()
        self._closed = False
        self._lock = threading.Lock()

        self.buffer = RingBuffer(self.config.buffer_size, self._flush_entries)
        self._timer: threading.Timer | None = None
        self._start_flush_timer()

    def send(self, entry: LogEntry):
        """异步发送一条日志"""
        if self._closed:
            logger.warning("Client 已关闭，日志丢弃")
            return
        entry.host = self.hostname
        entry.process_id = self.pid
        entry.environment = self.config.environment
        entry.project_slug = self.config.project_slug
        entry.service_name = self.config.service_name
        entry.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.buffer.push(entry)

    def close(self):
        """优雅关闭"""
        self._closed = True
        if self._timer:
            self._timer.cancel()
        remaining = self.buffer.flush()
        if remaining:
            try:
                self._send_batch(remaining)
            except Exception as e:
                logger.error(f"关闭时上报失败: {e}")
                self.offline_cache.save(remaining)
        self.offline_cache.flush_all(self._send_batch)

    def fastapi_middleware(self):
        """返回 FastAPI/Starlette 中间件"""
        from .middleware import FastAPIMiddleware
        return FastAPIMiddleware(self)

    def flask_middleware(self):
        """返回 Flask 中间件（预留）"""
        raise NotImplementedError("Flask 中间件将在下一个版本支持")

    def _flush_entries(self, entries):
        """异步发送（在单独线程中执行）"""
        threading.Thread(target=self._flush_sync, args=(entries,), daemon=True).start()

    def _flush_sync(self, entries):
        for attempt in range(self.config.max_retries + 1):
            try:
                self._send_batch(entries)
                return
            except Exception as e:
                if attempt == self.config.max_retries:
                    logger.error(f"上报失败(重试{self.config.max_retries}次): {e}")
                    self.offline_cache.save(entries)
                else:
                    time.sleep(0.5 * (2 ** attempt))

    def _send_batch(self, entries):
        body = json.dumps({"logs": [e.to_dict() for e in entries]})
        resp = httpx.post(self.config.endpoint, content=body,
            headers={"Content-Type": "application/json", "X-API-Key": self.config.api_key,
                     "X-SDK-Type": "python", "X-SDK-Version": "0.3.0"},
            timeout=15)
        if resp.status_code not in (200, 201):
            raise Exception(f"服务端返回 {resp.status_code}")

    def _start_flush_timer(self):
        def _loop():
            while not self._closed:
                time.sleep(self.config.flush_interval)
                if self._closed: break
                entries = self.buffer.flush()
                if entries:
                    self._flush_entries(entries)
        threading.Thread(target=_loop, daemon=True).start()
