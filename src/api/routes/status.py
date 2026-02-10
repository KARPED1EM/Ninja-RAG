"""状态接口"""

from pathlib import Path

from fastapi import APIRouter, Depends

from src.api.schemas.sync_schemas import SyncStatusDTO, SystemStatusResponse
from src.infrastructure.container import Container
from src.service.document_service import DocumentService

router = APIRouter(prefix="/api", tags=["status"])


def get_container() -> Container:
    """获取容器"""
    return Container()


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(container: Container = Depends(get_container)):
    """获取系统状态"""
    document_service = container.document_service()
    sync_state_repo = container.sync_state_repository()
    vector_repo = container.vector_store_repository()
    graph_repo = container.graph_repository()
    settings = container.config()

    # 统计 raw 目录的 JSON 文件数量
    raw_file_count = 0
    data_dir = Path(settings.data_dir)
    if data_dir.exists():
        for category_dir in data_dir.iterdir():
            if category_dir.is_dir():
                for doc_dir in category_dir.iterdir():
                    if doc_dir.is_dir() and (doc_dir / "parse.json").exists():
                        raw_file_count += 1

    # 获取已加载文档数量（数据库记录）
    loaded_count = await document_service.get_document_count()

    # 获取向量数量
    try:
        vector_count = await vector_repo.count()
    except Exception:
        vector_count = 0

    # 获取图谱节点数量
    try:
        node_count = await graph_repo.count_nodes()
    except Exception:
        node_count = 0

    # 获取同步状态
    sync_states = await sync_state_repo.get_all_states()
    sync_state_dtos = [
        SyncStatusDTO(
            document_id=state.document_id,
            file_path=state.file_path,
            last_synced_at=state.last_synced_at.isoformat(),
            sync_status=state.sync_status,
            error_message=state.error_message,
        )
        for state in sync_states
    ]

    # 获取最后同步时间
    last_sync = None
    if sync_states:
        last_sync = max(state.last_synced_at for state in sync_states).isoformat()

    return SystemStatusResponse(
        raw_files=raw_file_count,
        mysql_documents=loaded_count,
        milvus_vectors=vector_count,
        neo4j_nodes=node_count,
        last_sync=last_sync,
        sync_states=sync_state_dtos,
    )
