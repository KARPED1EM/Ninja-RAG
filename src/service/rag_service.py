"""RAG 核心服务"""

import logging
import re

from src.domain.entities.query_result import QueryResult
from src.service.hybrid_search_service import HybridSearchService
from src.service.knowledge_graph_service import KnowledgeGraphService
from src.service.llm_service import LLMService
from src.service.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class RAGService:
    """RAG 核心服务（混合检索+图谱融合）"""

    def __init__(
        self,
        hybrid_search: HybridSearchService,
        kg_service: KnowledgeGraphService,
        llm_service: LLMService,
        text_normalizer: TextNormalizer,
        default_top_k: int = 5,
        enable_kg: bool = True,
        kg_weight: float = 0.4,
    ):
        self._search = hybrid_search
        self._kg_service = kg_service
        self._llm = llm_service
        self._normalizer = text_normalizer
        self._default_top_k = default_top_k
        self._enable_kg = enable_kg
        self._kg_weight = kg_weight

    async def query(self, question: str, top_k: int | None = None) -> QueryResult:
        """查询"""
        if top_k is None:
            top_k = self._default_top_k

        logger.info(f"原始查询: {question}")

        # 0. 文本规范化（繁→简）
        normalized_question = self._normalizer.normalize(question)
        if normalized_question != question:
            logger.info(f"规范化后: {normalized_question}")

        # 1. 意图识别（使用规范化后的问题）
        intent = self._llm.classify_intent(normalized_question)
        logger.info(f"意图: {intent}")

        # 2. 混合检索（Dense + Sparse + HyDE）- 使用规范化后的问题
        vector_sources = await self._search.search(normalized_question, top_k=top_k)
        logger.info(f"混合检索: 找到 {len(vector_sources)} 个来源")

        # 3. 图谱查询（如果启用）
        graph_paths = []
        if self._enable_kg:
            # 提取实体并规范化
            entities = intent.get("entities", [])
            normalized_entities = self._normalizer.normalize_list(entities)
            logger.info(f"提取到 {len(entities)} 个实体: {entities}")
            if normalized_entities != entities:
                logger.info(f"实体规范化: {normalized_entities}")

            # 只要有实体就尝试查询（降低门槛）
            if normalized_entities:
                try:
                    graph_paths = await self._kg_service.query_relationship(
                        normalized_entities, max_depth=3
                    )
                    logger.info(f"图谱查询: 找到 {len(graph_paths)} 条路径")
                except Exception as e:
                    logger.error(f"图谱查询失败: {e}")

        # 4. 融合上下文
        context = self._merge_contexts(vector_sources, graph_paths)
        logger.info(f"上下文长度: {len(context)} 字符")

        # 5. 生成答案（使用原始问题，保持用户体验）
        sources = [
            f"{s.section_title} (评分: {s.score:.2f})" for s in vector_sources
        ]
        answer, prompt = self._llm.generate_answer(question, context, sources)

        return QueryResult(
            question=question,
            answer=answer,
            vector_sources=vector_sources,
            graph_paths=graph_paths,
            confidence=self._calculate_confidence(vector_sources, graph_paths),
            context=context,
            prompt=prompt,
        )

    def _merge_contexts(self, vector_sources, graph_paths) -> str:
        """融合向量和图谱上下文"""
        contexts = []

        # 向量检索上下文
        if vector_sources:
            contexts.append("## 相关文档片段\n")
            for i, source in enumerate(vector_sources, 1):
                # 清理内容中的纯数字引用标记
                cleaned_content = self._remove_numeric_references(source.content)
                contexts.append(
                    f"{i}. {source.section_title}\n{cleaned_content}\n"
                )

        # 图谱推理上下文
        if graph_paths:
            contexts.append("\n## 知识图谱关系\n")
            for i, path in enumerate(graph_paths, 1):
                contexts.append(f"{i}. {path.path_description}\n")

        return "\n".join(contexts)

    @staticmethod
    def _remove_numeric_references(text: str) -> str:
        """
        移除文本中的纯数字引用标记（如 [1], [123] 等）
        保留包含非数字字符的中括号（如 [注1], [来源], [ref]）
        """
        # 匹配：左括号 + 可选空格 + 纯数字 + 可选空格 + 右括号
        pattern = r"\[\s*\d+\s*\]"
        return re.sub(pattern, "", text)

    def _calculate_confidence(self, vector_sources, graph_paths) -> float:
        """计算置信度"""
        confidence = 0.0

        # 向量检索置信度
        if vector_sources:
            avg_score = sum(s.score for s in vector_sources) / len(vector_sources)
            confidence += avg_score * (1 - self._kg_weight)

        # 图谱推理置信度
        if graph_paths:
            confidence += self._kg_weight

        return min(confidence, 1.0)
