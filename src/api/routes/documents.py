"""文档管理接口"""

from fastapi import APIRouter, Depends

from src.api.schemas.document_schemas import DocumentListResponse, DocumentSummaryDTO
from src.infrastructure.container import Container
from src.service.document_service import DocumentService

router = APIRouter(prefix="/api", tags=["documents"])


def get_document_service(
    container: Container = Depends(lambda: Container())
) -> DocumentService:
    """获取文档服务"""
    return container.document_service()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    document_service: DocumentService = Depends(get_document_service),
):
    """获取所有文档"""
    documents = await document_service.get_all_documents()

    document_dtos = [
        DocumentSummaryDTO(
            id=str(doc.id),
            title=doc.title,
            category=doc.category.value,
            page_id=doc.page_id,
            section_count=len(doc.sections),
            wikibase_item=doc.wikibase_item,
        )
        for doc in documents
    ]

    return DocumentListResponse(
        total=len(document_dtos),
        documents=document_dtos,
    )
