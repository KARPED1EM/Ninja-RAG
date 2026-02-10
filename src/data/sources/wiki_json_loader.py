"""维基 JSON 数据加载器"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import aiofiles


@dataclass
class WikiRawData:
    """维基原始数据"""

    category: str
    name: str
    parse_data: dict
    pageprops_data: dict
    imageinfo_data: dict
    file_path: str
    file_mtime: datetime


class WikiJsonLoader:
    """维基 JSON 加载器"""

    def __init__(self, data_dir: str):
        self._data_dir = Path(data_dir)

    async def scan_all(self) -> AsyncIterator[WikiRawData]:
        """扫描所有文档"""
        if not self._data_dir.exists():
            return

        for category_dir in self._data_dir.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name

            for doc_dir in category_dir.iterdir():
                if not doc_dir.is_dir():
                    continue

                name = doc_dir.name

                try:
                    raw_data = await self._load_document(category, name, doc_dir)
                    yield raw_data
                except Exception as e:
                    print(f"加载文档失败: {category}/{name} - {e}")

    async def load_document(
        self, category: str, name: str
    ) -> WikiRawData | None:
        """加载单个文档"""
        doc_dir = self._data_dir / category / name
        if not doc_dir.exists():
            return None

        try:
            return await self._load_document(category, name, doc_dir)
        except Exception as e:
            print(f"加载文档失败: {category}/{name} - {e}")
            return None

    async def _load_document(
        self, category: str, name: str, doc_dir: Path
    ) -> WikiRawData:
        """加载文档数据"""
        parse_file = doc_dir / "parse.json"
        pageprops_file = doc_dir / "pageprops.json"
        imageinfo_file = doc_dir / "imageinfo.json"

        # 读取 parse.json
        async with aiofiles.open(parse_file, "r", encoding="utf-8") as f:
            content = await f.read()
            parse_data = json.loads(content)

        # 读取 pageprops.json
        if pageprops_file.exists():
            async with aiofiles.open(pageprops_file, "r", encoding="utf-8") as f:
                content = await f.read()
                pageprops_data = json.loads(content)
        else:
            pageprops_data = {}

        # 读取 imageinfo.json
        if imageinfo_file.exists():
            async with aiofiles.open(imageinfo_file, "r", encoding="utf-8") as f:
                content = await f.read()
                imageinfo_data = json.loads(content)
        else:
            imageinfo_data = {}

        # 获取文件修改时间
        stat = os.stat(parse_file)
        file_mtime = datetime.fromtimestamp(stat.st_mtime)

        return WikiRawData(
            category=category,
            name=name,
            parse_data=parse_data,
            pageprops_data=pageprops_data,
            imageinfo_data=imageinfo_data,
            file_path=str(parse_file),
            file_mtime=file_mtime,
        )

    def get_all_document_paths(self) -> list[tuple[str, str, str]]:
        """
        获取所有文档路径
        返回 [(category, name, file_path), ...]
        """
        paths = []
        if not self._data_dir.exists():
            return paths

        for category_dir in self._data_dir.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name

            for doc_dir in category_dir.iterdir():
                if not doc_dir.is_dir():
                    continue

                name = doc_dir.name
                parse_file = doc_dir / "parse.json"

                if parse_file.exists():
                    paths.append((category, name, str(parse_file)))

        return paths
