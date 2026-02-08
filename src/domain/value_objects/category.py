"""文档分类枚举"""

from enum import Enum


class Category(str, Enum):
    """文档分类"""

    WORK = "作品"
    CHARACTER = "角色"
    CONCEPT = "概念"
    META = "元信息"

    @classmethod
    def from_str(cls, value: str) -> "Category":
        """从字符串创建"""
        for category in cls:
            if category.value == value:
                return category
        raise ValueError(f"无效的分类: {value}")
