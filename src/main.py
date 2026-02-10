"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.routes import documents, health, query, status, sync
from src.infrastructure.container import Container
from src.ui import routes as ui_routes

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("应用启动...")

    # 初始化容器
    container = Container()
    app.state.container = container

    # 初始化系统
    startup_service = container.startup_service()
    await startup_service.initialize_system()

    yield

    # 关闭系统
    logger.info("应用关闭...")
    await startup_service.shutdown()


# 创建应用
app = FastAPI(
    title="Ninja-RAG API",
    description="火影忍者知识库 RAG 系统",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册 API 路由
app.include_router(health.router)
app.include_router(query.router)
app.include_router(documents.router)
app.include_router(sync.router)
app.include_router(status.router)

# 注册 UI 路由
app.include_router(ui_routes.router)

logger.info("FastAPI 应用创建完成")
