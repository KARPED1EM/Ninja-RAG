"""查询相关的 DTO"""

from pydantic import BaseModel, Field


class VectorSourceDTO(BaseModel):
    """向量检索来源 DTO"""

    document_id: str
    section_title: str
    content: str
    score: float


class GraphPathDTO(BaseModel):
    """图谱路径 DTO"""

    start_entity: str
    end_entity: str
    path_length: int
    relationships: list[str]
    path_description: str


class QueryRequest(BaseModel):
    """查询请求"""

    question: str = Field(..., min_length=1, max_length=500, description="用户问题")
    top_k: int | None = Field(default=None, ge=1, le=20, description="返回结果数量")


class QueryResponse(BaseModel):
    """查询响应"""

    question: str
    answer: str
    vector_sources: list[VectorSourceDTO]
    graph_paths: list[GraphPathDTO]
    confidence: float = Field(..., ge=0.0, le=1.0)
    context: str = Field(default="", description="传递给 LLM 的上下文")
    prompt: str = Field(default="", description="完整的提示词")
