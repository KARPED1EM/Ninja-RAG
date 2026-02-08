"""维基数据到图谱实体的映射器"""

from src.domain.entities.document import Document
from src.domain.entities.kg_entity import KGEntity
from src.domain.entities.kg_relation import KGRelation
from src.domain.value_objects.entity_type import EntityType
from src.domain.value_objects.relation_type import RelationType


class WikiGraphMapper:
    """维基数据到图谱实体的映射器"""

    def extract_entities_from_document(self, document: Document) -> list[KGEntity]:
        """从文档中提取实体"""
        entities = []

        # 文档本身作为主实体
        entity_type = self._map_category_to_entity_type(document.category.value)
        main_entity = KGEntity(
            id=str(document.id),
            name=document.title,
            type=entity_type,
            properties={
                "page_id": document.page_id,
                "wikibase_item": document.wikibase_item or "",
                "category": document.category.value,
            },
        )
        entities.append(main_entity)

        return entities

    def extract_relations_from_document(
        self, document: Document
    ) -> list[KGRelation]:
        """从文档中提取关系"""
        relations = []

        # 提取链接关系
        for link in document.links:
            if link and link != document.title:
                relations.append(
                    KGRelation(
                        from_entity=document.title,
                        to_entity=link,
                        relation_type=RelationType.LINKS_TO,
                        properties={"source": "wiki_links"},
                    )
                )

        # 提取分类关系
        for category in document.categories:
            if category:
                relations.append(
                    KGRelation(
                        from_entity=document.title,
                        to_entity=category,
                        relation_type=RelationType.HAS_CATEGORY,
                        properties={"source": "wiki_categories"},
                    )
                )

        return relations

    def _map_category_to_entity_type(self, category: str) -> EntityType:
        """映射文档分类到实体类型"""
        mapping = {
            "作品": EntityType.WORK,
            "角色": EntityType.CHARACTER,
            "概念": EntityType.CONCEPT,
            "元信息": EntityType.META,
        }
        return mapping.get(category, EntityType.CONCEPT)
