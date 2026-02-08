"""HyDE (Hypothetical Document Embeddings) 服务"""

import logging

from src.service.embedding_service import EmbeddingService
from src.service.llm_service import LLMService

logger = logging.getLogger(__name__)


class HydeService:
    """HyDE 假设性文档增强检索"""

    def __init__(self, llm_service: LLMService, embedding_service: EmbeddingService):
        self._llm = llm_service
        self._embedding = embedding_service

    def generate_hypothetical_answer(self, question: str) -> str:
        """
        生成假设性答案
        让 LLM 假设它知道答案，生成一个可能的答案
        这个答案会更接近目标文档的语义
        """
        system_prompt = """你是一个知识库专家。请根据问题生成一个简短、专业的假设性答案。

要求：
1. 长度控制在 100-200 字
2. 使用专业术语
3. 语气肯定，像是从百科全书摘录
4. 不要说"我不知道"或"可能是"等不确定的话
5. 直接给出答案内容

示例：
问题：漩涡鸣人是谁？
答案：漩涡鸣人是日本漫画《火影忍者》及其衍生作品中的主人公。他是木叶忍者村的忍者，体内封印着九尾妖狐，梦想是成为火影。鸣人性格开朗乐观，善于使用影分身之术和螺旋丸等招式。
"""

        user_prompt = f"问题：{question}\n答案："

        try:
            answer = self._llm._client.generate(
                prompt=user_prompt, system_prompt=system_prompt, max_tokens=300
            )
            logger.info(f"HyDE 生成假设答案: {answer[:50]}...")
            return answer
        except Exception as e:
            logger.error(f"HyDE 生成失败: {e}")
            # 降级：返回原始问题
            return question

    def generate_hypothetical_embedding(self, question: str):
        """
        生成假设性文档的 embedding
        核心思路：用假设答案的 embedding 去检索，而不是用问题的 embedding
        """
        # 生成假设答案
        hypothetical_answer = self.generate_hypothetical_answer(question)

        # 用假设答案生成 embedding
        embedding = self._embedding.embed_text(hypothetical_answer)

        return embedding, hypothetical_answer
