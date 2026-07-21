"""日志管理平台 Python SDK — FastAPI/Starlette/Flask 中间件，一行代码接入日志采集。

使用方法:
    from logs_sdk import LogSDK
    logger = LogSDK(endpoint="https://api.logs.codexs.cn/api/v1/ingest/logs",
                    api_key="clog_pk_xxx", api_secret="clog_sk_xxx",
                    project_slug="my-project")
    app.add_middleware(logger.fastapi_middleware)  # FastAPI
"""

from .client import LogSDK
from .types import LogEntry, LogConfig

__version__ = "0.3.3"
__all__ = ["LogSDK", "LogEntry", "LogConfig"]
