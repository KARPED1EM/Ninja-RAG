"""文档实体与数据库模型的映射器"""

import json

from src.data.models import DocumentModel
from src.domain.entities.document import Document
from src.domain.value_objects.category import Category
from src.domain.value_objects.document_id import DocumentId


class DocumentDBMapper:
    """文档实体与数据库模型映射器"""

    def to_model(self, document: Document) -> DocumentModel:
        """实体 → 数据库模型"""
        raw_json = {
            "title": document.title,
            "page_id": document.page_id,
            "category": document.category.value,
            "wikibase_item": document.wikibase_item,
            "links": document.links,
            "categories": document.categories,
            "sections": [
                {
                    "title": section.title,
                    "content": section.content,
                    "level": section.level,
                    "index": section.index,
                }
                for section in document.sections
            ],
        }

        return DocumentModel(
            id=str(document.id),
            title=document.title,
            category=document.category.value,
            page_id=document.page_id,
            wikibase_item=document.wikibase_item,
            raw_json=raw_json,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    def from_model(self, model: DocumentModel) -> Document:
        """数据库模型 → 实体"""
        from src.domain.entities.section import Section

        raw_json = model.raw_json

        sections = [
            Section(
                title=s["title"],
                content=s["content"],
                level=s["level"],
                index=s["index"],
            )
            for s in raw_json.get("sections", [])
        ]

        return Document(
            id=DocumentId.from_str(model.id),
            title=model.title,
            category=Category.from_str(model.category),
            page_id=model.page_id,
            sections=sections,
            wikibase_item=raw_json.get("wikibase_item"),
            links=raw_json.get("links", []),
            categories=raw_json.get("categories", []),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
