"""文档 ID 值对象"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentId:
    """文档唯一标识（category/name）"""

    category: str
    name: str

    def __str__(self) -> str:
        return f"{self.category}/{self.name}"

    @classmethod
    def from_str(cls, value: str) -> "DocumentId":
        """从字符串创建"""
        parts = value.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"无效的文档 ID 格式: {value}")
        return cls(category=parts[0], name=parts[1])
