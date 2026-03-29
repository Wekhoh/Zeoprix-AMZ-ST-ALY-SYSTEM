"""
FastAPI 后端应用入口。

V1 先提供可部署、可探活的后端骨架，后续再逐步接入认证、
工作区、分析任务与导出能力。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI


APP_TITLE = "AMZ 搜索词分析系统 Backend"
APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """预留后端资源初始化入口。"""
    yield


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    @app.get("/", tags=["system"])
    async def read_root() -> dict[str, str]:
        return {
            "service": APP_TITLE,
            "status": "ok",
            "version": APP_VERSION,
        }

    @app.get("/health", tags=["system"])
    async def healthcheck() -> dict[str, str]:
        return {
            "service": APP_TITLE,
            "status": "ok",
            "version": APP_VERSION,
        }

    return app


app = create_app()
