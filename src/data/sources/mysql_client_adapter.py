"""MySQL 客户端适配器"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import Database


class MySQLClientAdapter:
    """MySQL 客户端适配器"""

    def __init__(self, database: Database):
        self._database = database

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        async with self._database.get_session() as session:
            yield session

    async def create_tables(self) -> None:
        """创建所有表"""
        await self._database.create_all_tables()

    async def drop_tables(self) -> None:
        """删除所有表"""
        await self._database.drop_all_tables()

    async def close(self) -> None:
        """关闭连接"""
        await self._database.close()
