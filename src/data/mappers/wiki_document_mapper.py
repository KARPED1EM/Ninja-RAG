"""维基数据到文档实体的映射器"""

import logging

from bs4 import BeautifulSoup

from src.data.sources.wiki_json_loader import WikiRawData
from src.domain.entities.document import Document
from src.domain.entities.section import Section
from src.domain.value_objects.category import Category
from src.domain.value_objects.document_id import DocumentId
from src.service.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class WikiDocumentMapper:
    """维基数据映射器"""

    def __init__(self, text_normalizer: TextNormalizer | None = None):
        """初始化映射器

        Args:
            text_normalizer: 文本规范化服务（可选，用于简繁转换）
        """
        self._normalizer = text_normalizer

    def map_to_document(self, raw_data: WikiRawData) -> Document:
        """映射为文档实体"""
        parse_data = raw_data.parse_data.get("parse", {})

        # 提取基本信息
        title = parse_data.get("title", raw_data.name)
        page_id = parse_data.get("pageid", 0)

        # 规范化标题（繁→简）
        if self._normalizer:
            title = self._normalizer.normalize(title)

        # 提取 wikibase_item
        pages = raw_data.pageprops_data.get("query", {}).get("pages", [])
        if pages:
            first_page = pages[0]
            wikibase_item = first_page.get("pageprops", {}).get("wikibase_item")
        else:
            wikibase_item = None

        # 提取链接并规范化
        links = []
        for link in parse_data.get("links", []):
            if "title" in link:
                link_title = link["title"]
                if self._normalizer:
                    link_title = self._normalizer.normalize(link_title)
                links.append(link_title)

        # 提取分类并规范化
        categories = []
        for cat in parse_data.get("categories", []):
            if "category" in cat:
                cat_name = cat["category"].replace("Category:", "")
                if self._normalizer:
                    cat_name = self._normalizer.normalize(cat_name)
                categories.append(cat_name)

        # 提取章节（内部会规范化文本）
        sections = self._extract_sections(parse_data)

        # 创建文档
        document = Document(
            id=DocumentId(category=raw_data.category, name=raw_data.name),
            title=title,
            category=Category.from_str(raw_data.category),
            page_id=page_id,
            sections=sections,
            wikibase_item=wikibase_item,
            links=links,
            categories=categories,
            created_at=raw_data.file_mtime,
            updated_at=raw_data.file_mtime,
        )

        return document

    def _extract_sections(self, parse_data: dict) -> list[Section]:
        """提取章节（基于 HTML 标题分割）"""
        sections = []

        # 获取 HTML 内容
        html_content = parse_data.get("text", "")
        if isinstance(html_content, dict):
            html_content = html_content.get("*", "")

        if not html_content:
            return sections

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_content, "lxml")

        # 移除不需要的元素
        for tag in soup.find_all(["script", "style", "table"]):
            tag.decompose()
        for tag in soup.find_all("div", class_=["navbox", "infobox", "toc", "mw-editsection"]):
            tag.decompose()

        # 基于标题分割章节
        current_section = {"title": "概述", "content": [], "level": 1}
        section_index = 0

        for element in soup.find_all(["h2", "h3", "p"]):
            if element.name in ["h2", "h3"]:
                # 保存当前章节
                if current_section["content"]:
                    content = "\n\n".join(current_section["content"])
                    if content.strip():
                        sections.append(
                            Section(
                                title=current_section["title"],
                                content=content,
                                level=current_section["level"],
                                index=section_index,
                            )
                        )
                        section_index += 1

                # 开始新章节
                title = element.get_text(strip=True)
                # 移除编辑链接等
                title = title.replace("[编辑]", "").strip()
                # 规范化标题
                if title and self._normalizer:
                    title = self._normalizer.normalize(title)
                current_section = {
                    "title": title or f"章节{section_index + 1}",
                    "content": [],
                    "level": 2 if element.name == "h2" else 3,
                }
            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    # 规范化段落文本
                    if self._normalizer:
                        text = self._normalizer.normalize(text)
                    current_section["content"].append(text)

        # 保存最后一个章节
        if current_section["content"]:
            content = "\n\n".join(current_section["content"])
            if content.strip():
                sections.append(
                    Section(
                        title=current_section["title"],
                        content=content,
                        level=current_section["level"],
                        index=section_index,
                    )
                )

        # 如果没有提取到章节，回退到全文本
        if not sections:
            text = soup.get_text(strip=True)
            if text:
                # 规范化全文本
                if self._normalizer:
                    text = self._normalizer.normalize(text)
                sections.append(
                    Section(title="内容", content=text, level=1, index=0)
                )

        return sections
