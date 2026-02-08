"""实体提取领域服务"""

from src.domain.entities.document import Document
from src.domain.entities.kg_entity import KGEntity
from src.domain.entities.kg_relation import KGRelation
from src.domain.value_objects.entity_type import EntityType
from src.domain.value_objects.relation_type import RelationType


class EntityExtractor:
    """实体提取业务逻辑"""

    def extract_entities_from_text(self, text: str) -> list[KGEntity]:
        """从文本中提取实体（简单实现）"""
        # 这里返回空列表，实际提取由 LLM 完成
        return []

    def extract_relations_from_text(self, text: str) -> list[KGRelation]:
        """从文本中提取关系（简单实现）"""
        # 这里返回空列表，实际提取由 LLM 完成
        return []

    def merge_entities(self, entities: list[KGEntity]) -> list[KGEntity]:
        """合并重复实体"""
        seen = {}
        merged = []

        for entity in entities:
            key = entity.name.lower()
            if key not in seen:
                seen[key] = entity
                merged.append(entity)
            else:
                # 合并属性
                existing = seen[key]
                existing.properties.update(entity.properties)

        return merged

    def merge_relations(self, relations: list[KGRelation]) -> list[KGRelation]:
        """合并重复关系"""
        seen = set()
        merged = []

        for relation in relations:
            key = (
                relation.from_entity.lower(),
                relation.relation_type.value,
                relation.to_entity.lower(),
            )
            if key not in seen:
                seen.add(key)
                merged.append(relation)

        return merged

    def validate_entity(self, entity: KGEntity) -> bool:
        """验证实体有效性"""
        # 检查名称长度
        if len(entity.name) < 2 or len(entity.name) > 100:
            return False

        # 检查是否为噪声
        noise_words = {"的", "了", "是", "在", "和", "有", "与", "及", "等"}
        if entity.name in noise_words:
            return False

        return True

    def validate_relation(self, relation: KGRelation) -> bool:
        """验证关系有效性"""
        # 检查实体名称
        if not relation.from_entity or not relation.to_entity:
            return False

        # 避免自环
        if relation.from_entity == relation.to_entity:
            return False

        return True
