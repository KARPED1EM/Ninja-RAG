"""知识图谱服务"""

import logging

from src.data.mappers.wiki_graph_mapper import WikiGraphMapper
from src.data.repositories.graph_repository import IGraphRepository
from src.domain.entities.document import Document
from src.domain.entities.query_result import GraphPath
from src.domain.services.entity_extractor import EntityExtractor
from src.service.llm_service import LLMService

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """知识图谱服务"""

    def __init__(
        self,
        graph_repository: IGraphRepository,
        wiki_graph_mapper: WikiGraphMapper,
        entity_extractor: EntityExtractor,
        llm_service: LLMService,
        enable_llm_extract: bool = True,
    ):
        self._graph_repo = graph_repository
        self._mapper = wiki_graph_mapper
        self._extractor = entity_extractor
        self._llm = llm_service
        self._enable_llm_extract = enable_llm_extract

    async def build_graph_from_document(self, document: Document) -> dict:
        """从文档构建图谱"""
        stats = {"nodes": 0, "edges": 0}

        # 1. 提取结构化实体和关系
        entities = self._mapper.extract_entities_from_document(document)
        relations = self._mapper.extract_relations_from_document(document)

        # 2. LLM 补充提取（如果启用）
        if self._enable_llm_extract:
            try:
                # 从文档内容提取
                full_text = document.get_full_text()
                if full_text and len(full_text) < 5000:  # 限制文本长度
                    llm_entities, llm_relations = (
                        self._llm.extract_entities_and_relations(full_text[:5000])
                    )
                    entities.extend(llm_entities)
                    relations.extend(llm_relations)
            except Exception as e:
                logger.error(f"LLM 提取失败: {e}")

        # 3. 去重和验证
        entities = self._extractor.merge_entities(entities)
        entities = [e for e in entities if self._extractor.validate_entity(e)]

        relations = self._extractor.merge_relations(relations)
        relations = [r for r in relations if self._extractor.validate_relation(r)]

        # 4. 批量创建节点（单个查询）
        if entities:
            try:
                created = await self._graph_repo.create_entities_batch(entities)
                stats["nodes"] = created
            except Exception as e:
                logger.error(f"批量创建节点失败: {e}")

        # 5. 批量创建关系（单个查询）
        if relations:
            try:
                created = await self._graph_repo.create_relations_batch(relations)
                stats["edges"] = created
            except Exception as e:
                logger.error(f"批量创建关系失败: {e}")

        return stats

    async def query_relationship(
        self, entity_names: list[str], max_depth: int = 3
    ) -> list[GraphPath]:
        """关系查询"""
        if not entity_names:
            return []

        # 单个实体时，查找其所有关系
        if len(entity_names) == 1:
            logger.info(f"单实体查询: {entity_names[0]}")
            try:
                related = await self._graph_repo.find_related_entities(
                    entity_names[0], relation_type=None, max_depth=1
                )
                logger.info(f"找到 {len(related)} 个相关实体")

                # 将相关实体转换为 GraphPath 格式
                paths = []
                for rel in related[:10]:  # 限制数量避免过多
                    path = GraphPath(
                        start_entity=entity_names[0],
                        end_entity=rel.get("entity", ""),
                        path_length=1,
                        relationships=[rel.get("relation", "")],
                        path_description=f"{entity_names[0]} {rel.get('relation', '')} {rel.get('entity', '')}"
                    )
                    paths.append(path)
                return paths
            except Exception as e:
                logger.error(f"单实体查询失败: {e}")
                return []

        # 多个实体时，查找实体间的路径
        return await self._graph_repo.find_paths(entity_names, max_depth)

    async def find_related_entities(
        self, entity_name: str, relation_type: str | None = None, max_depth: int = 2
    ) -> list[dict]:
        """查找相关实体"""
        return await self._graph_repo.find_related_entities(
            entity_name, relation_type, max_depth
        )

    async def clear_graph(self) -> None:
        """清空图谱"""
        await self._graph_repo.clear()
