"""LLM 服务"""

from src.domain.entities.kg_entity import KGEntity
from src.domain.entities.kg_relation import KGRelation
from src.domain.value_objects.entity_type import EntityType
from src.domain.value_objects.relation_type import RelationType
from src.infrastructure.external.qwen_client import QwenClient


class LLMService:
    """LLM 服务"""

    def __init__(self, qwen_client: QwenClient):
        self._client = qwen_client

    def generate_answer(
        self, question: str, context: str, sources: list[str] | None = None
    ) -> tuple[str, str]:
        """生成答案，返回 (答案, 完整提示词)"""
        return self._client.generate_answer(question, context, sources)

    def extract_entities_and_relations(
        self, text: str
    ) -> tuple[list[KGEntity], list[KGRelation]]:
        """从文本中提取实体和关系"""
        try:
            result = self._client.extract_entities(text)

            entities = []
            for entity_data in result.get("entities", []):
                try:
                    entity = KGEntity(
                        id=f"entity_{entity_data['name']}",
                        name=entity_data["name"],
                        type=EntityType.from_str(entity_data["type"]),
                        properties={},
                    )
                    entities.append(entity)
                except (KeyError, ValueError):
                    continue

            relations = []
            for rel_data in result.get("relations", []):
                try:
                    relation = KGRelation(
                        from_entity=rel_data["from"],
                        to_entity=rel_data["to"],
                        relation_type=RelationType.from_str(rel_data["relation"]),
                        properties={},
                    )
                    relations.append(relation)
                except (KeyError, ValueError):
                    continue

            return entities, relations
        except Exception as e:
            print(f"LLM 提取失败: {e}")
            return [], []

    def classify_intent(self, question: str) -> dict:
        """意图识别"""
        system_prompt = """从用户问题中提取关键实体（人名、组织、术语等）。

要求：
1. 识别问题中的所有人物、组织、地点、概念等实体
2. 实体名称要准确完整（如"漩涡鸣人"而不是"鸣人"）
3. 尽可能多地提取实体，即使只有一个也要提取

返回 JSON 格式：
{
  "intent": "事实查询|关系推理|描述解释",
  "entities": ["实体1", "实体2", ...]
}

只返回 JSON，不要其他解释。"""

        prompt = f"问题：{question}\n\n提取实体："

        result = self._client.generate(
            prompt, system_prompt=system_prompt, temperature=0.1
        )

        # 解析 JSON
        import json

        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                json_str = result[start:end]
                return json.loads(json_str)
            else:
                return {"intent": "事实查询", "entities": []}
        except json.JSONDecodeError:
            return {"intent": "事实查询", "entities": []}
