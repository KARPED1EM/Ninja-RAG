"""嵌入向量值对象"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingVector:
    """嵌入向量"""

    values: tuple[float, ...]

    def __post_init__(self):
        if not self.values:
            raise ValueError("向量不能为空")

    @classmethod
    def from_list(cls, values: list[float]) -> "EmbeddingVector":
        """从列表创建"""
        return cls(values=tuple(values))

    def to_list(self) -> list[float]:
        """转换为列表"""
        return list(self.values)

    @property
    def dimension(self) -> int:
        """向量维度"""
        return len(self.values)
