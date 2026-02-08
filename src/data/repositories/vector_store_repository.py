"""向量存储仓库实现"""

from typing import Protocol

from src.data.sources.milvus_client_adapter import MilvusClientAdapter
from src.domain.entities.query_result import VectorSource
from src.domain.value_objects.document_id import DocumentId
from src.domain.value_objects.embedding_vector import EmbeddingVector


class IVectorStoreRepository(Protocol):
    """向量存储仓库接口"""

    async def index_vectors(
        self,
        doc_id: DocumentId,
        chunks: list[tuple[str, str, EmbeddingVector]],
    ) -> int: ...

    async def search(
        self, query_vector: EmbeddingVector, top_k: int = 5
    ) -> list[VectorSource]: ...

    async def delete_by_document(self, doc_id: DocumentId) -> int: ...

    async def count(self) -> int: ...


class MilvusVectorStoreRepository:
    """基于 Milvus 的向量存储仓库实现"""

    def __init__(self, milvus_adapter: MilvusClientAdapter, collection_name: str):
        self._milvus = milvus_adapter
        self._collection_name = collection_name

    async def index_vectors(
        self,
        doc_id: DocumentId,
        chunks: list[tuple[str, str, EmbeddingVector]],
    ) -> int:
        """
        索引向量
        chunks: [(section_title, content, embedding), ...]
        """
        if not chunks:
            return 0

        # 准备数据
        data = []
        for i, (section_title, content, embedding) in enumerate(chunks):
            chunk_id = f"{doc_id}#{i}"
            data.append(
                {
                    "id": chunk_id,
                    "document_id": str(doc_id),
                    "section_title": section_title,
                    "content": content,
                    "embedding": embedding.to_list(),
                }
            )

        # 插入数据
        result = self._milvus.insert(self._collection_name, data)
        return result.get("insert_count", 0)

    async def search(
        self, query_vector: EmbeddingVector, top_k: int = 5
    ) -> list[VectorSource]:
        """向量检索"""
        results = self._milvus.search(
            self._collection_name,
            query_vectors=[query_vector.to_list()],
            top_k=top_k,
            output_fields=["document_id", "section_title", "content"],
        )

        # 解析结果
        sources = []
        if results and len(results) > 0:
            for hit in results[0]:
                entity = hit["entity"]
                sources.append(
                    VectorSource(
                        document_id=entity.get("document_id", ""),
                        section_title=entity.get("section_title", ""),
                        content=entity.get("content", ""),
                        score=hit["score"],
                    )
                )

        return sources

    async def delete_by_document(self, doc_id: DocumentId) -> int:
        """删除文档的所有向量"""
        expr = f'document_id == "{doc_id}"'
        result = self._milvus.delete(self._collection_name, expr)
        return result.get("delete_count", 0)

    async def count(self) -> int:
        """获取向量总数"""
        collection = self._milvus._client.get_collection(self._collection_name)
        return collection.num_entities
