"""文档处理领域服务"""

from src.domain.entities.document import Document
from src.domain.entities.section import Section


class DocumentProcessor:
    """文档处理业务逻辑"""

    def clean_text(self, text: str) -> str:
        """清洗文本"""
        # 移除多余空白
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    def split_into_chunks(
        self, document: Document, max_length: int = 512
    ) -> list[tuple[str, str]]:
        """
        分块
        返回 [(section_title, chunk_content), ...]
        """
        chunks = []
        for section in document.sections:
            content = self.clean_text(section.content)
            if len(content) <= max_length:
                chunks.append((section.title, content))
            else:
                # 按句子分块
                sentences = self._split_sentences(content)
                current_chunk = []
                current_length = 0

                for sentence in sentences:
                    sentence_len = len(sentence)
                    if current_length + sentence_len > max_length and current_chunk:
                        # 保存当前块
                        chunks.append((section.title, "".join(current_chunk)))
                        current_chunk = [sentence]
                        current_length = sentence_len
                    else:
                        current_chunk.append(sentence)
                        current_length += sentence_len

                # 保存最后一块
                if current_chunk:
                    chunks.append((section.title, "".join(current_chunk)))

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """按句子分割"""
        import re

        # 中文句子分隔符
        separators = r"[。！？;；\n]"
        sentences = re.split(f"({separators})", text)

        # 重新组合句子和分隔符
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])

        return [s for s in result if s.strip()]

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """提取关键词（简单实现）"""
        # 简单的词频统计
        import re
        from collections import Counter

        # 移除标点
        text = re.sub(r"[^\w\s]", " ", text)
        words = text.split()

        # 过滤短词和常见词
        stop_words = {"的", "了", "是", "在", "和", "有", "与", "及", "等", "中", "为"}
        words = [w for w in words if len(w) > 1 and w not in stop_words]

        # 统计词频
        counter = Counter(words)
        return [word for word, _ in counter.most_common(top_n)]
