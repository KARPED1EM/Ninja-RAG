"""知识图谱三元组"""

from dataclasses import dataclass

from src.domain.entities.kg_entity import KGEntity
from src.domain.entities.kg_relation import KGRelation


@dataclass
class KGTriple:
    """知识图谱三元组（主体-关系-客体）"""

    subject: KGEntity
    relation: KGRelation
    object: KGEntity

    def __post_init__(self):
        if self.relation.from_entity != self.subject.name:
            raise ValueError("关系的起点实体与主体实体不匹配")
        if self.relation.to_entity != self.object.name:
            raise ValueError("关系的终点实体与客体实体不匹配")

    def __str__(self) -> str:
        return f"({self.subject.name})-[{self.relation.relation_type.value}]->({self.object.name})"
