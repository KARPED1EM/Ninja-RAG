"""同步状态仓库实现"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import delete, select

from src.data.models import SyncStateModel
from src.domain.value_objects.document_id import DocumentId
from src.infrastructure.database import Database


class ISyncStateRepository(Protocol):
    """同步状态仓库接口"""

    async def get_state(self, doc_id: DocumentId) -> SyncStateModel | None: ...

    async def save_state(
        self,
        doc_id: DocumentId,
        file_path: str,
        file_mtime: datetime,
        status: str,
        error_message: str | None = None,
        file_hash: str | None = None,
    ) -> None: ...

    async def get_all_states(self) -> list[SyncStateModel]: ...

    async def delete_state(self, doc_id: DocumentId) -> None: ...


class MySQLSyncStateRepository:
    """基于 MySQL 的同步状态仓库实现"""

    def __init__(self, database: Database):
        self._database = database

    async def get_state(self, doc_id: DocumentId) -> SyncStateModel | None:
        """获取同步状态"""
        async with self._database.get_session() as session:
            result = await session.execute(
                select(SyncStateModel).where(
                    SyncStateModel.document_id == str(doc_id)
                )
            )
            return result.scalar_one_or_none()

    async def save_state(
        self,
        doc_id: DocumentId,
        file_path: str,
        file_mtime: datetime,
        status: str,
        error_message: str | None = None,
        file_hash: str | None = None,
    ) -> None:
        """保存同步状态"""
        async with self._database.get_session() as session:
            model = SyncStateModel(
                document_id=str(doc_id),
                file_path=file_path,
                file_hash=file_hash,
                file_mtime=file_mtime,
                last_synced_at=datetime.now(),
                sync_status=status,
                error_message=error_message,
            )
            await session.merge(model)

    async def get_all_states(self) -> list[SyncStateModel]:
        """获取所有同步状态"""
        async with self._database.get_session() as session:
            result = await session.execute(select(SyncStateModel))
            return list(result.scalars().all())

    async def delete_state(self, doc_id: DocumentId) -> None:
        """删除同步状态"""
        async with self._database.get_session() as session:
            await session.execute(
                delete(SyncStateModel).where(
                    SyncStateModel.document_id == str(doc_id)
                )
            )
