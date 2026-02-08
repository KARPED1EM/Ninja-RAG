"""BM25 稀疏检索服务"""

import asyncio
import logging
import pickle
from pathlib import Path
from typing import Any

import jieba
from rank_bm25 import BM25Okapi

from src.domain.entities.query_result import VectorSource

logger = logging.getLogger(__name__)


class BM25Service:
    """BM25 关键词检索服务"""

    def __init__(self, cache_dir: str = ".cache/bm25"):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._corpus: list[dict[str, Any]] = []  # 存储文档信息
        self._tokenized_corpus: list[list[str]] = []  # 分词后的语料
        self._bm25: BM25Okapi | None = None
        self._lock = asyncio.Lock()

    async def build_index(self, documents: list[dict[str, Any]]) -> None:
        """
        构建 BM25 索引
        documents: [{"id": str, "document_id": str, "section_title": str, "content": str}, ...]
        """
        async with self._lock:
            logger.info(f"构建 BM25 索引，文档数: {len(documents)}")

            self._corpus = documents
            self._tokenized_corpus = []

            # 分词
            for doc in documents:
                tokens = list(jieba.cut_for_search(doc["content"]))
                self._tokenized_corpus.append(tokens)

            # 构建 BM25
            self._bm25 = BM25Okapi(self._tokenized_corpus)

            logger.info("BM25 索引构建完成")

    async def search(self, query: str, top_k: int = 5) -> list[VectorSource]:
        """
        BM25 检索
        返回格式与向量检索一致，方便后续融合
        """
        if not self._bm25 or not self._corpus:
            logger.warning("BM25 索引未构建，返回空结果")
            return []

        # 分词
        query_tokens = list(jieba.cut_for_search(query))

        # 检索
        scores = self._bm25.get_scores(query_tokens)

        # 排序并取 top-k
        top_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 只返回有得分的
                doc = self._corpus[idx]
                results.append(
                    VectorSource(
                        document_id=doc["document_id"],
                        section_title=doc["section_title"],
                        content=doc["content"],
                        score=float(scores[idx]),  # BM25 原始分数
                    )
                )

        return results

    async def save_index(self) -> None:
        """保存索引到磁盘"""
        async with self._lock:
            if not self._bm25:
                return

            cache_file = self._cache_dir / "bm25_index.pkl"
            data = {
                "corpus": self._corpus,
                "tokenized_corpus": self._tokenized_corpus,
                "bm25": self._bm25,
            }

            with open(cache_file, "wb") as f:
                pickle.dump(data, f)

            logger.info(f"BM25 索引已保存到 {cache_file}")

    async def load_index(self) -> bool:
        """从磁盘加载索引"""
        cache_file = self._cache_dir / "bm25_index.pkl"

        if not cache_file.exists():
            return False

        async with self._lock:
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)

                self._corpus = data["corpus"]
                self._tokenized_corpus = data["tokenized_corpus"]
                self._bm25 = data["bm25"]

                logger.info(f"BM25 索引已从 {cache_file} 加载，文档数: {len(self._corpus)}")
                return True
            except Exception as e:
                logger.error(f"加载 BM25 索引失败: {e}")
                return False

    def is_ready(self) -> bool:
        """检查索引是否就绪"""
        return self._bm25 is not None and len(self._corpus) > 0
