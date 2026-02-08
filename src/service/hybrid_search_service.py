"""混合检索服务（Dense + Sparse）"""

import logging
from collections import defaultdict

from src.data.repositories.vector_store_repository import IVectorStoreRepository
from src.domain.entities.query_result import VectorSource
from src.domain.value_objects.embedding_vector import EmbeddingVector
from src.service.bm25_service import BM25Service
from src.service.embedding_service import EmbeddingService
from src.service.hyde_service import HydeService

logger = logging.getLogger(__name__)


class HybridSearchService:
    """混合检索服务"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: IVectorStoreRepository,
        bm25_service: BM25Service,
        hyde_service: HydeService | None = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        use_hyde: bool = False,
    ):
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._bm25 = bm25_service
        self._hyde = hyde_service
        self._dense_weight = dense_weight
        self._sparse_weight = sparse_weight
        self._use_hyde = use_hyde

    async def search(self, query: str, top_k: int = 5) -> list[VectorSource]:
        """
        混合检索
        使用 RRF (Reciprocal Rank Fusion) 融合稠密向量和稀疏检索结果
        """
        # 1. 稠密向量检索（可选使用 HyDE）
        if self._use_hyde and self._hyde:
            logger.info("使用 HyDE 增强检索")
            query_vec, hypothetical_answer = self._hyde.generate_hypothetical_embedding(
                query
            )
            logger.info(f"假设性答案: {hypothetical_answer[:100]}...")
        else:
            query_vec = self._embedding.embed_text(query)

        dense_results = await self._vector_store.search(query_vec, top_k=top_k * 2)
        logger.info(f"稠密检索: {len(dense_results)} 个结果")

        # 2. 稀疏检索（BM25）
        sparse_results = []
        if self._bm25.is_ready():
            sparse_results = await self._bm25.search(query, top_k=top_k * 2)
            logger.info(f"稀疏检索: {len(sparse_results)} 个结果")
        else:
            logger.warning("BM25 索引未就绪，跳过稀疏检索")

        # 3. 融合结果（RRF）
        if not sparse_results:
            # 如果没有 BM25 结果，直接返回稠密检索结果
            return dense_results[:top_k]

        fused_results = self._reciprocal_rank_fusion(
            dense_results, sparse_results, top_k
        )

        logger.info(f"混合检索融合后: {len(fused_results)} 个结果")
        return fused_results

    def _reciprocal_rank_fusion(
        self,
        dense_results: list[VectorSource],
        sparse_results: list[VectorSource],
        top_k: int,
        k: int = 60,
    ) -> list[VectorSource]:
        """
        RRF (Reciprocal Rank Fusion) 算法
        RRF(d) = sum(1 / (k + rank_i(d))) for all rankers i

        参数:
            k: 常数，通常取 60（平衡作用）
        """
        # 构建唯一键 -> VectorSource 映射
        doc_map: dict[str, VectorSource] = {}

        # 构建唯一键 -> RRF 分数映射
        rrf_scores: dict[str, float] = defaultdict(float)

        # 处理稠密检索结果
        for rank, source in enumerate(dense_results, start=1):
            key = f"{source.document_id}#{source.section_title}"
            doc_map[key] = source
            rrf_scores[key] += self._dense_weight * (1.0 / (k + rank))

        # 处理稀疏检索结果
        for rank, source in enumerate(sparse_results, start=1):
            key = f"{source.document_id}#{source.section_title}"
            if key not in doc_map:
                doc_map[key] = source
            rrf_scores[key] += self._sparse_weight * (1.0 / (k + rank))

        # 按 RRF 分数排序
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)

        # 构建最终结果，更新 score 为 RRF 分数
        results = []
        for key in sorted_keys[:top_k]:
            source = doc_map[key]
            # 更新 score 为 RRF 融合分数（归一化到 0-1）
            source.score = rrf_scores[key]
            results.append(source)

        return results

    def _weighted_fusion(
        self,
        dense_results: list[VectorSource],
        sparse_results: list[VectorSource],
        top_k: int,
    ) -> list[VectorSource]:
        """
        加权融合（备选方案）
        需要对 dense 和 sparse 的分数进行归一化
        """
        # 归一化稠密检索分数
        if dense_results:
            max_dense = max(s.score for s in dense_results)
            for source in dense_results:
                source.score = source.score / max_dense if max_dense > 0 else 0

        # 归一化稀疏检索分数
        if sparse_results:
            max_sparse = max(s.score for s in sparse_results)
            for source in sparse_results:
                source.score = source.score / max_sparse if max_sparse > 0 else 0

        # 合并并加权
        doc_map: dict[str, VectorSource] = {}
        scores: dict[str, float] = defaultdict(float)

        for source in dense_results:
            key = f"{source.document_id}#{source.section_title}"
            doc_map[key] = source
            scores[key] += self._dense_weight * source.score

        for source in sparse_results:
            key = f"{source.document_id}#{source.section_title}"
            if key not in doc_map:
                doc_map[key] = source
            scores[key] += self._sparse_weight * source.score

        # 排序
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

        results = []
        for key in sorted_keys[:top_k]:
            source = doc_map[key]
            source.score = scores[key]
            results.append(source)

        return results
