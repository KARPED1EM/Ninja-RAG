"""文档相关的 DTO"""

from pydantic import BaseModel


class DocumentSummaryDTO(BaseModel):
    """文档摘要 DTO"""

    id: str
    title: str
    category: str
    page_id: int
    section_count: int
    wikibase_item: str | None = None


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    total: int
    documents: list[DocumentSummaryDTO]
