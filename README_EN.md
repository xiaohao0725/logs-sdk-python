# Log Management Platform Python SDK

[中文文档](./README.md) | [PyPI](https://pypi.org/project/logs-sdk/)

`logs-sdk` provides FastAPI/Starlette and Flask middleware with one-line integration for automatic HTTP request log collection.

## Features

- ✅ **One-line**: `app.add_middleware(logger.fastapi_middleware)`
- ✅ **60+ fields**: request/response headers & body, client device info, TLS version
- ✅ **Auto-detect**: client type (Web/MiniProgram/App/Server), request origin
- ✅ **Error capture**: HTTP 5xx + Python exception stack trace
- ✅ **UUID v7**: 32-char hex without hyphens
- ✅ **Sanitization**: Authorization/Cookie auto-masking
- ✅ **Async**: ring buffer + background timer, non-blocking
- ✅ **Offline cache**: local file cache on failure, auto-retransmit
- ✅ **Graceful shutdown**: `close()` ensures all buffered logs are sent

## Installation

```bash
pip install logs-sdk
# or with FastAPI
pip install logs-sdk[fastapi]
```

Python 3.9+.

## Quick Start

```python
from fastapi import FastAPI
from logs_sdk import LogSDK

app = FastAPI()
logger = LogSDK(
    endpoint="https://api.logs.codexs.cn/api/v1/ingest/logs",
    api_key="clog_pk_xxx",
    api_secret="clog_sk_xxx",
    project_slug="my-project",
)
app.add_middleware(logger.fastapi_middleware)

@app.get("/api/hello")
def hello():
    return {"message": "hello"}
```

## Configuration / Collected Fields / Architecture

See [Go SDK README_EN.md](https://github.com/xiaohao0725/logs-sdk-go/blob/main/README_EN.md) — all SDKs share identical field definitions and architecture.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v0.3.0 | 2026-06-21 | Initial release: FastAPI/Flask middleware, async buffer, retry, offline cache |

## License

UNLICENSED — Internal use
