"""环形缓冲区 — 80% 自动触发 flush"""
import threading
from typing import List, Callable
from .types import LogEntry

class RingBuffer:
    def __init__(self, capacity: int, flush_fn: Callable):
        self.capacity = max(capacity, 100)
        self.buf = [None] * self.capacity
        self.head = 0
        self.tail = 0
        self.count = 0
        self.lock = threading.Lock()
        self.flush_fn = flush_fn

    def push(self, entry: LogEntry):
        with self.lock:
            self.buf[self.head] = entry
            self.head = (self.head + 1) % self.capacity
            self.count += 1
            if self.count >= self.capacity * 0.8:
                entries = self._drain()
                if self.flush_fn:
                    self.flush_fn(entries)

    def flush(self) -> List[LogEntry]:
        with self.lock:
            return self._drain()

    @property
    def length(self) -> int:
        return self.count

    def _drain(self) -> List[LogEntry]:
        entries = []
        while self.count > 0:
            if self.buf[self.tail]:
                entries.append(self.buf[self.tail])
            self.buf[self.tail] = None
            self.tail = (self.tail + 1) % self.capacity
            self.count -= 1
        return entries
