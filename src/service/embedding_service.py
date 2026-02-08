"""嵌入服务"""

from src.domain.value_objects.embedding_vector import EmbeddingVector
from src.infrastructure.external.bge_embedder import BgeEmbedder


class EmbeddingService:
    """嵌入服务"""

    def __init__(self, bge_embedder: BgeEmbedder):
        self._embedder = bge_embedder

    def embed_text(self, text: str) -> EmbeddingVector:
        """嵌入单个文本"""
        values = self._embedder.embed_text(text)
        return EmbeddingVector.from_list(values)

    def embed_texts(self, texts: list[str]) -> list[EmbeddingVector]:
        """批量嵌入文本"""
        values_list = self._embedder.embed_texts(texts)
        return [EmbeddingVector.from_list(values) for values in values_list]

    def embed_chunks(
        self, chunks: list[tuple[str, str]]
    ) -> list[tuple[str, str, EmbeddingVector]]:
        """
        嵌入文本块
        输入: [(section_title, content), ...]
        输出: [(section_title, content, embedding), ...]
        """
        texts = [content for _, content in chunks]
        embeddings = self.embed_texts(texts)

        return [
            (section_title, content, embedding)
            for (section_title, content), embedding in zip(chunks, embeddings)
        ]

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._embedder.dimension
