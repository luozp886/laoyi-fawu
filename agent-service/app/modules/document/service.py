from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.models import DocumentTemplate, GeneratedDocument
from app.modules.document.repository import (
    CasePlanRepository,
    DocumentTemplateRepository,
    GeneratedDocumentRepository,
)


class DocumentTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = DocumentTemplateRepository(session)

    async def list_templates(self, category: str | None) -> list[DocumentTemplate]:
        return await self.repository.find_by_category(category)

    async def get_template(self, template_id: int) -> DocumentTemplate | None:
        return await self.repository.find_by_id(template_id)


class CasePlanService:
    """维权方案的落库（供 Agent 的 save_case_plan 工具调用）"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = CasePlanRepository(session)

    async def create_plan(
        self,
        *,
        user_id: int,
        plan_name: str,
        summary: str | None,
        case_profile: dict[str, Any],
        items: list[dict[str, Any]],
    ) -> UUID:
        try:
            plan = await self.repository.create(
                user_id=user_id,
                plan_name=plan_name,
                summary=summary,
                case_profile=case_profile,
                items=items,
            )
            await self.session.commit()
            return plan.id
        except Exception:
            await self.session.rollback()
            raise


class GeneratedDocumentService:
    """已生成文书：落库、查询、标记下载"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = GeneratedDocumentRepository(session)

    async def save_generated(
        self,
        *,
        user_id: int,
        plan_id: UUID | None,
        template_id: int,
        title: str,
        elements: dict[str, Any],
        law_citations: list[dict[str, Any]],
        body_text: str | None,
        html: str | None,
    ) -> UUID:
        try:
            doc = await self.repository.create(
                user_id=user_id,
                plan_id=plan_id,
                template_id=template_id,
                title=title,
                elements=elements,
                law_citations=law_citations,
                body_text=body_text,
                html=html,
            )
            await self.session.commit()
            return doc.id
        except Exception:
            await self.session.rollback()
            raise

    async def list_my_documents(self, user_id: int) -> list[GeneratedDocument]:
        return await self.repository.find_by_user(user_id)

    async def get_document(self, user_id: int, doc_id: UUID) -> GeneratedDocument | None:
        doc = await self.repository.find_by_id(doc_id)
        if doc is None or doc.user_id != user_id:
            return None
        return doc

    async def mark_downloaded(self, doc_id: UUID) -> None:
        await self.repository.mark_downloaded(doc_id)
        await self.session.commit()
