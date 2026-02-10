"""关系类型枚举"""

from enum import Enum


class RelationType(str, Enum):
    """知识图谱关系类型"""

    PARENT_OF = "父子"
    TEACHER_OF = "师徒"
    CREATED_BY = "创作者"
    BELONGS_TO = "属于"
    OPPOSES = "对抗"
    HAS = "拥有"
    LINKS_TO = "链接"
    HAS_CATEGORY = "分类"

    @classmethod
    def from_str(cls, value: str) -> "RelationType":
        """从字符串创建"""
        for relation_type in cls:
            if relation_type.value == value:
                return relation_type
        raise ValueError(f"无效的关系类型: {value}")
