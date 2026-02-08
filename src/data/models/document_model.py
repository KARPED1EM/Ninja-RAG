"""文档数据模型"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from .base import Base


class DocumentModel(Base):
    """文档表模型"""

    __tablename__ = "documents"

    id = Column(String(255), primary_key=True, comment="文档唯一标识 (category/name)")
    title = Column(String(500), nullable=False, comment="文档标题")
    category = Column(String(100), nullable=False, index=True, comment="文档分类")
    page_id = Column(Integer, nullable=False, unique=True, comment="维基页面 ID")
    wikibase_item = Column(String(100), nullable=True, comment="Wikidata 项目 ID")
    raw_json = Column(JSON, nullable=False, comment="原始 JSON 数据")
    created_at = Column(
        DateTime, default=datetime.now, nullable=False, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<DocumentModel(id={self.id}, title={self.title})>"
