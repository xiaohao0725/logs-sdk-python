"""离线缓存 — 网络故障时缓存到本地文件，恢复后自动重传"""
import json, os, tempfile, time, logging
from typing import List, Callable
from .types import LogEntry

logger = logging.getLogger("logs-sdk")

class OfflineCache:
    def __init__(self, directory: str = ""):
        self.dir = directory or os.path.join(tempfile.gettempdir(), "logs-sdk-offline")
        self.max_size = 50 * 1024 * 1024
        self.max_age = 24 * 3600
        self.enabled = True
        os.makedirs(self.dir, exist_ok=True)

    def save(self, entries: List[LogEntry]):
        if not self.enabled or not entries: return
        self._cleanup()
        filename = os.path.join(self.dir, f"offline-{time.strftime('%Y%m%dT%H%M%S')}.json")
        try:
            with open(filename, "w") as f:
                json.dump([e.to_dict() for e in entries], f)
            logger.info(f"离线缓存已保存: {filename} ({len(entries)} 条)")
        except Exception as e:
            logger.error(f"离线缓存保存失败: {e}")

    def flush_all(self, send_fn: Callable):
        files = [f for f in os.listdir(self.dir) if f.startswith("offline-") and f.endswith(".json")]
        if not files: return
        for fn in sorted(files):
            filepath = os.path.join(self.dir, fn)
            try:
                if time.time() - os.path.getmtime(filepath) > self.max_age:
                    os.remove(filepath)
                    continue
                with open(filepath) as f:
                    data = json.load(f)
                entries = [LogEntry(**d) for d in data]
                send_fn(entries)
                os.remove(filepath)
                logger.info(f"离线缓存已重传: {fn} ({len(entries)} 条)")
            except Exception as e:
                logger.error(f"离线缓存重传失败: {e}")
                return

    def pending_count(self) -> int:
        return len([f for f in os.listdir(self.dir) if f.startswith("offline-")])

    def _cleanup(self):
        files = sorted([os.path.join(self.dir, f) for f in os.listdir(self.dir) if f.startswith("offline-")],
                       key=lambda x: os.path.getmtime(x))
        total = sum(os.path.getsize(f) for f in files if os.path.exists(f))
        for f in files:
            if total <= self.max_size: break
            if os.path.exists(f):
                total -= os.path.getsize(f)
                os.remove(f)
