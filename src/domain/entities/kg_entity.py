"""知识图谱实体"""

from dataclasses import dataclass, field
from typing import Any

from src.domain.value_objects.entity_type import EntityType


@dataclass
class KGEntity:
    """知识图谱实体"""

    id: str
    name: str
    type: EntityType
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ValueError("实体名称不能为空")

    def get_label(self) -> str:
        """获取 Neo4j 节点标签"""
        return self.type.value

    def to_neo4j_properties(self) -> dict[str, Any]:
        """转换为 Neo4j 属性"""
        props = {"id": self.id, "name": self.name, "type": self.type.value}
        props.update(self.properties)
        return props
