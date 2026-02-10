"""千问 API 客户端"""

import dashscope
from dashscope import Generation

from src.infrastructure.config.settings import Settings


class QwenClient:
    """通义千问 API 客户端"""

    def __init__(self, settings: Settings):
        self._settings = settings
        dashscope.api_key = settings.dashscope_api_key

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """生成回答"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = Generation.call(
            model=self._settings.qwen_model,
            messages=messages,
            temperature=temperature or self._settings.qwen_temperature,
            result_format="message",
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise Exception(
                f"千问 API 调用失败: {response.code} - {response.message}"
            )

    def extract_entities(self, text: str) -> dict:
        """从文本中提取实体和关系"""
        system_prompt = """你是一个专业的实体关系抽取助手。从文本中提取火影忍者相关的实体和关系。

实体类型：人物、概念、作品、组织、地点
关系类型：父子、师徒、创作者、属于、对抗、拥有

返回 JSON 格式：
{
  "entities": [{"name": "实体名称", "type": "实体类型"}],
  "relations": [{"from": "实体1", "relation": "关系类型", "to": "实体2"}]
}

只返回 JSON，不要其他解释。"""

        prompt = f"文本：\n{text}\n\n提取实体和关系："

        result = self.generate(prompt, system_prompt=system_prompt, temperature=0.1)

        # 解析 JSON
        import json

        try:
            # 提取 JSON 部分
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                json_str = result[start:end]
                return json.loads(json_str)
            else:
                return {"entities": [], "relations": []}
        except json.JSONDecodeError:
            return {"entities": [], "relations": []}

    def generate_answer(
        self, question: str, context: str, sources: list[str] | None = None
    ) -> tuple[str, str]:
        """基于上下文生成答案，返回 (答案, 完整提示词)"""
        system_prompt = """你是火影忍者知识库助手。基于提供的上下文回答用户问题。

要求：
1. 答案必须基于上下文，不要编造信息
2. 如果上下文不足以回答问题，明确说明
3. 回答要准确、简洁、专业
4. 使用中文"""

        sources_text = ""
        if sources:
            sources_text = "\n\n来源：\n" + "\n".join(
                f"- {source}" for source in sources
            )

        prompt = f"""上下文：
{context}

问题：{question}

请基于上下文回答问题。{sources_text}"""

        # 构建完整提示词（包含 system + user）
        full_prompt = f"""[System]\n{system_prompt}\n\n[User]\n{prompt}"""

        answer = self.generate(prompt, system_prompt=system_prompt)
        return answer, full_prompt
