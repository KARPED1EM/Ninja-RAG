"""数据库会话管理"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.data.models import Base
from src.infrastructure.config.settings import Settings


class Database:
    """数据库管理类"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def get_engine(self) -> AsyncEngine:
        """获取数据库引擎"""
        if self._engine is None:
            self._engine = create_async_engine(
                self._settings.mysql_url,
                echo=self._settings.debug,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """获取会话工厂"""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话上下文管理器"""
        session_factory = self.get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_all_tables(self) -> None:
        """创建所有表"""
        engine = self.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all_tables(self) -> None:
        """删除所有表"""
        engine = self.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._engine is not None:
            await self._engine.dispose()
