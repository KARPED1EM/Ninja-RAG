"""查询结果实体"""

from dataclasses import dataclass, field


@dataclass
class VectorSource:
    """向量检索来源"""

    document_id: str
    section_title: str
    content: str
    score: float


@dataclass
class GraphPath:
    """图谱路径"""

    start_entity: str
    end_entity: str
    path_length: int
    relationships: list[str] = field(default_factory=list)
    path_description: str = ""


@dataclass
class QueryResult:
    """查询结果"""

    question: str
    answer: str
    vector_sources: list[VectorSource] = field(default_factory=list)
    graph_paths: list[GraphPath] = field(default_factory=list)
    confidence: float = 0.0
    context: str = ""  # 传递给 LLM 的上下文
    prompt: str = ""  # 完整的提示词

    def has_graph_context(self) -> bool:
        """是否包含图谱上下文"""
        return len(self.graph_paths) > 0
