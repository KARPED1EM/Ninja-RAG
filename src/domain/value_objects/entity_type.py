"""实体类型枚举"""

from enum import Enum


class EntityType(str, Enum):
    """知识图谱实体类型"""

    CHARACTER = "人物"
    CONCEPT = "概念"
    WORK = "作品"
    ORGANIZATION = "组织"
    LOCATION = "地点"
    META = "元信息"

    @classmethod
    def from_str(cls, value: str) -> "EntityType":
        """从字符串创建"""
        for entity_type in cls:
            if entity_type.value == value:
                return entity_type
        raise ValueError(f"无效的实体类型: {value}")
