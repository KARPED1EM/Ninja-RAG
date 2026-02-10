"""查询接口"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas.query_schemas import (
    GraphPathDTO,
    QueryRequest,
    QueryResponse,
    VectorSourceDTO,
)
from src.infrastructure.container import Container
from src.service.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])


def get_rag_service(container: Container = Depends(lambda: Container())) -> RAGService:
    """获取 RAG 服务"""
    return container.rag_service()


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
):
    """问答查询"""
    try:
        logger.info(f"[查询API] 收到问题: {request.question}")
        result = await rag_service.query(request.question, top_k=request.top_k)

        logger.info(f"[查询API] 向量检索结果数: {len(result.vector_sources)}")
        logger.info(f"[查询API] 图谱路径数: {len(result.graph_paths)}")

        if result.graph_paths:
            for i, path in enumerate(result.graph_paths):
                logger.info(f"[查询API] 图谱路径 {i+1}: {path.start_entity} -> {path.end_entity}")

        # 转换为 DTO
        vector_sources = [
            VectorSourceDTO(
                document_id=s.document_id,
                section_title=s.section_title,
                content=s.content,
                score=s.score,
            )
            for s in result.vector_sources
        ]

        graph_paths = [
            GraphPathDTO(
                start_entity=p.start_entity,
                end_entity=p.end_entity,
                path_length=p.path_length,
                relationships=p.relationships,
                path_description=p.path_description,
            )
            for p in result.graph_paths
        ]

        return QueryResponse(
            question=result.question,
            answer=result.answer,
            vector_sources=vector_sources,
            graph_paths=graph_paths,
            confidence=result.confidence,
            context=result.context,
            prompt=result.prompt,
        )
    except Exception as e:
        logger.error(f"[查询API] 查询失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
