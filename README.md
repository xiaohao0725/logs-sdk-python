# 日志管理平台 Python SDK

[English Documentation](https://github.com/xiaohao0725/logs-sdk-python/blob/main/README_EN.md) | [PyPI](https://pypi.org/project/logs-sdk/)

`logs-sdk` 是日志管理平台的 Python SDK，提供 FastAPI/Starlette 和 Flask 中间件，一行代码即可自动采集 HTTP 请求的完整日志，异步批量上报。

## 功能特性

- ✅ **一行代码接入**：`app.add_middleware(logger.fastapi_middleware)`
- ✅ **完整采集**：60+ 字段——请求/响应头体、客户端信息、设备信息、TLS 版本
- ✅ **自动识别**：客户端类型（Web / 小程序 / App / 服务端）、请求来源
- ✅ **异常捕获**：HTTP 5xx + Python 异常堆栈自动采集
- ✅ **UUID v7**：32 位十六进制无连字符
- ✅ **敏感脱敏**：Authorization / Cookie 自动脱敏
- ✅ **异步非阻塞**：环形缓冲区 + 后台定时刷新
- ✅ **离线缓存**：断网本地存储，恢复自动重传
- ✅ **优雅关闭**：`close()` 确保缓冲日志全部上报

## 安装

```bash
pip install logs-sdk

# 或安装 FastAPI 集成
pip install logs-sdk[fastapi]
```

要求 Python 3.9+。

## 快速开始

### FastAPI / Starlette

```python
from fastapi import FastAPI
from logs_sdk import LogSDK

app = FastAPI()

logger = LogSDK(
    endpoint="https://api.logs.codexs.cn/api/v1/ingest/logs",
    api_key="clog_pk_xxx",
    api_secret="clog_sk_xxx",
    project_slug="my-project",
    environment="production",
)

# 一行代码接入
app.add_middleware(logger.fastapi_middleware)

@app.get("/api/hello")
def hello():
    return {"message": "hello"}
```

### Flask

```python
from flask import Flask
from logs_sdk import LogSDK

app = Flask(__name__)

logger = LogSDK(
    endpoint="https://api.logs.codexs.cn/api/v1/ingest/logs",
    api_key="clog_pk_xxx",
    api_secret="clog_sk_xxx",
    project_slug="my-project",
)

# Flask 中间件
app.wsgi_app = logger.flask_middleware
```

## 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `endpoint` | `str` | **必填** | 日志上报地址 |
| `api_key` | `str` | **必填** | SDK 认证密钥（公钥） |
| `api_secret` | `str` | **必填** | SDK 认证密钥（私钥） |
| `project_slug` | `str` | **必填** | 项目短标识 |
| `environment` | `str` | `"production"` | 运行环境 |
| `service_name` | `str` | `""` | 微服务名称 |
| `buffer_size` | `int` | `1000` | 缓冲区容量 |
| `flush_interval` | `int` | `5` | 刷新间隔（秒） |
| `max_retries` | `int` | `3` | 最大重试次数 |
| `max_body_size` | `int` | `4096` | 请求/响应体最大采集大小 |

## 采集字段一览

与 Go/Node.js/Java SDK 完全对齐，详见 [LogEntry 类型定义](./src/logs_sdk/types.py)。

## 架构设计

```
HTTP 请求进入
  │
  ├─ ① FastAPIMiddleware.dispatch()
  │     ├─ 生成 UUID v7
  │     ├─ 读取请求体
  │     └─ 记录开始时间
  │
  ├─ ② await call_next(request)  # 业务处理
  │
  ├─ ③ 构建 LogEntry（60+ 字段）
  │
  ├─ ④ buffer.push(entry)  # 非阻塞
  │
  └─ ⑤ 后台定时刷新 → POST → 重试 → 离线缓存
```

## 离线缓存

断网时自动缓存到 `$TMPDIR/logs-sdk-offline/`，恢复后自动重传。

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.3.0 | 2026-06-21 | 初始版本：FastAPI/Flask 中间件、异步缓冲、重试、离线缓存 |

## License

UNLICENSED — 内部使用
