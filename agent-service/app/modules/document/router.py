from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.infra.database import get_session
from app.modules.document.schemas import (
    DocumentTemplateResponse,
    GeneratedDocumentListResponse,
    GeneratedDocumentResponse,
)
from app.modules.document.service import (
    DocumentTemplateService,
    GeneratedDocumentService,
)

router = APIRouter(prefix="/api/v1", tags=["documents"])


def _get_template_service(session: AsyncSession = Depends(get_session)) -> DocumentTemplateService:
    return DocumentTemplateService(session)


def _get_doc_service(session: AsyncSession = Depends(get_session)) -> GeneratedDocumentService:
    return GeneratedDocumentService(session)


@router.get("/templates", response_model=list[DocumentTemplateResponse])
async def list_templates(
    category: str | None = None,
    service: DocumentTemplateService = Depends(_get_template_service),
) -> list[DocumentTemplateResponse]:
    return await service.list_templates(category)


@router.get("/templates/{template_id}", response_model=DocumentTemplateResponse)
async def get_template(
    template_id: int = Path(gt=0),
    service: DocumentTemplateService = Depends(_get_template_service),
) -> DocumentTemplateResponse:
    template = await service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="文书模板不存在")
    return template


# 说明：示例实现未接入完整鉴权中间件，user_id 从会话上下文中解析。
# 与 chat 模块一致，暂以固定演示用户为准，后续接入统一鉴权。

@router.get("/documents", response_model=list[GeneratedDocumentListResponse])
async def list_my_documents(
    service: GeneratedDocumentService = Depends(_get_doc_service),
) -> list[GeneratedDocumentResponse]:
    # 演示用户 id=1
    return await service.list_my_documents(user_id=1)


@router.get("/documents/{doc_id}", response_model=GeneratedDocumentResponse)
async def get_document(
    doc_id: UUID,
    service: GeneratedDocumentService = Depends(_get_doc_service),
) -> GeneratedDocumentResponse:
    doc = await service.get_document(user_id=1, doc_id=doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文书不存在")
    return doc
