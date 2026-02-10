"""章节实体"""

from dataclasses import dataclass


@dataclass
class Section:
    """文档章节"""

    title: str
    content: str
    level: int
    index: int

    def __post_init__(self):
        if not self.content.strip():
            raise ValueError("章节内容不能为空")

    def get_full_title(self, parent_title: str = "") -> str:
        """获取完整标题"""
        if parent_title:
            return f"{parent_title} > {self.title}"
        return self.title
