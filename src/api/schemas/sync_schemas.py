"""同步相关的 DTO"""

from pydantic import BaseModel


class SyncResponse(BaseModel):
    """同步响应"""

    total: int
    success: int
    failed: int
    added: int = 0
    updated: int = 0
    deleted: int = 0
    vector_count: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    errors: list[str] = []


class SyncStatusDTO(BaseModel):
    """同步状态 DTO"""

    document_id: str
    file_path: str
    last_synced_at: str
    sync_status: str
    error_message: str | None = None


class SystemStatusResponse(BaseModel):
    """系统状态响应"""

    raw_files: int  # raw 目录中的源文档数量
    mysql_documents: int  # 已加载到数据库的文档数量
    milvus_vectors: int  # 向量数量
    neo4j_nodes: int  # 图谱节点数量
    last_sync: str | None = None
    sync_states: list[SyncStatusDTO]
