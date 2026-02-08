"""文档实体"""

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.section import Section
from src.domain.value_objects.category import Category
from src.domain.value_objects.document_id import DocumentId


@dataclass
class Document:
    """文档实体"""

    id: DocumentId
    title: str
    category: Category
    page_id: int
    sections: list[Section] = field(default_factory=list)
    wikibase_item: str | None = None
    links: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.title:
            raise ValueError("文档标题不能为空")
        if self.page_id <= 0:
            raise ValueError("页面 ID 必须大于 0")

    def get_full_text(self) -> str:
        """获取完整文本"""
        texts = [self.title]
        for section in self.sections:
            texts.append(f"{section.title}: {section.content}")
        return "\n\n".join(texts)

    def get_chunks(self, max_length: int = 512) -> list[tuple[str, str]]:
        """
        分块
        返回 [(section_title, chunk_content), ...]
        """
        chunks = []
        for section in self.sections:
            content = section.content
            if len(content) <= max_length:
                chunks.append((section.title, content))
            else:
                # 简单分块，按最大长度切分
                for i in range(0, len(content), max_length):
                    chunk = content[i : i + max_length]
                    chunks.append((section.title, chunk))
        return chunks
