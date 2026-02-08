"""文本规范化服务（简繁转换）"""

import logging

from opencc import OpenCC

logger = logging.getLogger(__name__)


class TextNormalizer:
    """文本规范化服务

    统一将文本转换为简体中文，解决简繁混杂导致的匹配问题
    """

    def __init__(self):
        """初始化 OpenCC 转换器"""
        try:
            # 繁体转简体（支持多种繁体标准）
            self._t2s = OpenCC("t2s")  # Traditional to Simplified
            logger.info("文本规范化服务已初始化（繁→简）")
        except Exception as e:
            logger.error(f"OpenCC 初始化失败: {e}")
            self._t2s = None

    def normalize(self, text: str) -> str:
        """规范化文本为简体中文

        Args:
            text: 原始文本（可能包含繁体）

        Returns:
            简体中文文本
        """
        if not text or not self._t2s:
            return text

        try:
            return self._t2s.convert(text)
        except Exception as e:
            logger.error(f"文本规范化失败: {e}")
            return text

    def normalize_list(self, texts: list[str]) -> list[str]:
        """批量规范化文本

        Args:
            texts: 文本列表

        Returns:
            规范化后的文本列表
        """
        return [self.normalize(text) for text in texts]
