"""文档仓库实现"""

from typing import Protocol

from sqlalchemy import delete, select

from src.data.mappers.document_db_mapper import DocumentDBMapper
from src.data.models import DocumentModel
from src.domain.entities.document import Document
from src.domain.value_objects.document_id import DocumentId
from src.infrastructure.database import Database


class IDocumentRepository(Protocol):
    """文档仓库接口"""

    async def get_by_id(self, doc_id: DocumentId) -> Document | None: ...

    async def get_all(self) -> list[Document]: ...

    async def save(self, document: Document) -> None: ...

    async def delete(self, doc_id: DocumentId) -> None: ...

    async def exists(self, doc_id: DocumentId) -> bool: ...

    async def count(self) -> int: ...


class MySQLDocumentRepository:
    """基于 MySQL 的文档仓库实现"""

    def __init__(self, database: Database, mapper: DocumentDBMapper):
        self._database = database
        self._mapper = mapper

    async def get_by_id(self, doc_id: DocumentId) -> Document | None:
        """根据 ID 获取文档"""
        async with self._database.get_session() as session:
            result = await session.execute(
                select(DocumentModel).where(DocumentModel.id == str(doc_id))
            )
            model = result.scalar_one_or_none()
            if model:
                return self._mapper.from_model(model)
            return None

    async def get_all(self) -> list[Document]:
        """获取所有文档"""
        async with self._database.get_session() as session:
            result = await session.execute(select(DocumentModel))
            models = result.scalars().all()
            return [self._mapper.from_model(model) for model in models]

    async def save(self, document: Document) -> None:
        """保存文档"""
        async with self._database.get_session() as session:
            model = self._mapper.to_model(document)
            await session.merge(model)

    async def delete(self, doc_id: DocumentId) -> None:
        """删除文档"""
        async with self._database.get_session() as session:
            await session.execute(
                delete(DocumentModel).where(DocumentModel.id == str(doc_id))
            )

    async def exists(self, doc_id: DocumentId) -> bool:
        """检查文档是否存在"""
        async with self._database.get_session() as session:
            result = await session.execute(
                select(DocumentModel.id).where(DocumentModel.id == str(doc_id))
            )
            return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """获取文档总数"""
        from sqlalchemy import func

        async with self._database.get_session() as session:
            result = await session.execute(select(func.count(DocumentModel.id)))
            return result.scalar() or 0
