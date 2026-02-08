"""文档管理服务"""

from src.data.repositories.document_repository import IDocumentRepository
from src.domain.entities.document import Document
from src.domain.value_objects.document_id import DocumentId


class DocumentService:
    """文档管理服务"""

    def __init__(self, document_repository: IDocumentRepository):
        self._repository = document_repository

    async def get_document(self, doc_id: DocumentId) -> Document | None:
        """获取文档"""
        return await self._repository.get_by_id(doc_id)

    async def get_all_documents(self) -> list[Document]:
        """获取所有文档"""
        return await self._repository.get_all()

    async def save_document(self, document: Document) -> None:
        """保存文档"""
        await self._repository.save(document)

    async def delete_document(self, doc_id: DocumentId) -> None:
        """删除文档"""
        await self._repository.delete(doc_id)

    async def document_exists(self, doc_id: DocumentId) -> bool:
        """检查文档是否存在"""
        return await self._repository.exists(doc_id)

    async def get_document_count(self) -> int:
        """获取文档总数"""
        return await self._repository.count()
