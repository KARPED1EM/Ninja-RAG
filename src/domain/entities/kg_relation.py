"""知识图谱关系"""

from dataclasses import dataclass, field
from typing import Any

from src.domain.value_objects.relation_type import RelationType


@dataclass
class KGRelation:
    """知识图谱关系"""

    from_entity: str
    to_entity: str
    relation_type: RelationType
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.from_entity or not self.to_entity:
            raise ValueError("实体引用不能为空")

    def get_cypher_type(self) -> str:
        """获取 Cypher 关系类型"""
        # 转换为大写蛇形命名
        return self.relation_type.name

    def to_neo4j_properties(self) -> dict[str, Any]:
        """转换为 Neo4j 属性"""
        return self.properties.copy()
