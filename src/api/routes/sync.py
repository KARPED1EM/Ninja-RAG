"""同步接口"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from src.api.schemas.sync_schemas import SyncResponse
from src.infrastructure.container import Container
from src.service.sync_service import SyncProgress, SyncService

router = APIRouter(prefix="/api/sync", tags=["sync"])


def get_sync_service(container: Container = Depends(lambda: Container())) -> SyncService:
    """获取同步服务"""
    return container.sync_service()


@router.post("/full", response_model=SyncResponse)
async def full_sync(
    sync_service: SyncService = Depends(get_sync_service),
):
    """全量同步（实际执行增量同步）"""
    result = await sync_service.incremental_sync()

    return SyncResponse(
        total=result.total,
        success=result.success,
        failed=result.failed,
        added=result.added,
        updated=result.updated,
        deleted=result.deleted,
        errors=result.errors,
    )


@router.post("/incremental", response_model=SyncResponse)
async def incremental_sync(
    sync_service: SyncService = Depends(get_sync_service),
):
    """增量同步"""
    result = await sync_service.incremental_sync()

    return SyncResponse(
        total=result.total,
        success=result.success,
        failed=result.failed,
        added=result.added,
        updated=result.updated,
        deleted=result.deleted,
        errors=result.errors,
    )


@router.get("/incremental/stream")
async def incremental_sync_stream(
    sync_service: SyncService = Depends(get_sync_service),
):
    """增量同步（SSE 流式进度）"""

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 事件生成器（带心跳）"""
        progress_queue: asyncio.Queue[SyncProgress | None] = asyncio.Queue()

        async def progress_callback(progress: SyncProgress):
            """进度回调"""
            await progress_queue.put(progress)

        # 设置进度回调
        sync_service.set_progress_callback(progress_callback)

        # 启动同步任务
        async def run_sync():
            try:
                result = await sync_service.incremental_sync()
                await progress_queue.put(None)  # 结束标记
                return result
            except Exception as e:
                logger.exception("同步任务异常")
                await progress_queue.put(
                    SyncProgress(
                        phase="错误",
                        current=0,
                        total=0,
                        message=f"同步失败: {str(e)}",
                    )
                )
                await progress_queue.put(None)
                raise

        # 在后台运行同步
        sync_task = asyncio.create_task(run_sync())

        # 发送初始消息
        yield f"data: {json.dumps({'type': 'started', 'message': '同步任务已启动'}, ensure_ascii=False)}\n\n"

        # 流式发送进度（带超时检测）
        try:
            while True:
                try:
                    # 等待进度更新，最多15秒
                    progress = await asyncio.wait_for(progress_queue.get(), timeout=15.0)

                    if progress is None:
                        # 同步完成，发送最终结果
                        result = await sync_task
                        yield f"data: {json.dumps({'type': 'result', 'data': {'total': result.total, 'success': result.success, 'failed': result.failed, 'added': result.added, 'updated': result.updated, 'deleted': result.deleted, 'errors': result.errors}}, ensure_ascii=False)}\n\n"
                        break
                    else:
                        # 发送进度
                        yield f"data: {json.dumps({'type': 'progress', 'data': {'phase': progress.phase, 'current': progress.current, 'total': progress.total, 'current_doc': progress.current_doc, 'message': progress.message}}, ensure_ascii=False)}\n\n"

                except asyncio.TimeoutError:
                    # 超时，发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat', 'message': '同步进行中...'}, ensure_ascii=False)}\n\n"
                    continue

        except Exception as e:
            logger.exception("SSE流异常")
            yield f"data: {json.dumps({'type': 'error', 'message': f'内部错误: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/clear/knowledge")
async def clear_knowledge_base(
    container: Container = Depends(lambda: Container())
):
    """
    清空知识库
    删除所有向量、图谱数据，但保留文档记录和同步状态
    """
    try:
        # 清空 Milvus 向量
        milvus_client = container.milvus_client()
        collection_name = container.config().milvus_collection
        milvus_client.drop_collection(collection_name)
        # 重新创建集合
        embedding_dim = container.config().embedding_dim
        milvus_client.create_collection(
            collection_name, embedding_dim, description="火影忍者知识库"
        )

        # 清空 Neo4j 图谱
        neo4j_client = container.neo4j_client()
        await neo4j_client.clear_database()

        return {
            "success": True,
            "message": "知识库已清空（向量 + 图谱），文档记录已保留",
        }

    except Exception as e:
        return {"success": False, "message": f"清空失败: {str(e)}"}


@router.post("/clear/all")
async def clear_all_data(
    container: Container = Depends(lambda: Container())
):
    """
    清空所有数据
    删除文档记录、向量、图谱、同步状态等所有数据
    """
    try:
        # 清空 MySQL 文档表
        database = container.database()
        async with database.get_session() as session:
            await session.execute(text("DELETE FROM documents"))
            await session.execute(text("DELETE FROM sync_states"))
            await session.commit()

        # 清空 Milvus 向量
        milvus_client = container.milvus_client()
        collection_name = container.config().milvus_collection
        milvus_client.drop_collection(collection_name)
        # 重新创建集合
        embedding_dim = container.config().embedding_dim
        milvus_client.create_collection(
            collection_name, embedding_dim, description="火影忍者知识库"
        )

        # 清空 Neo4j 图谱
        neo4j_client = container.neo4j_client()
        await neo4j_client.clear_database()

        return {
            "success": True,
            "message": "所有数据已清空（文档 + 向量 + 图谱 + 同步状态）",
        }

    except Exception as e:
        return {"success": False, "message": f"清空失败: {str(e)}"}
