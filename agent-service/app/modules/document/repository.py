from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.models import (
    CasePlan,
    CasePlanItem,
    DocumentTemplate,
    GeneratedDocument,
)


class DocumentTemplateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_category(
        self,
        category: str | None,
    ) -> list[DocumentTemplate]:
        conditions: list[ColumnElement[bool]] = [DocumentTemplate.status == "active"]
        if category:
            conditions.append(DocumentTemplate.category == category)
        rows = await self.session.scalars(
            select(DocumentTemplate).where(*conditions).order_by(DocumentTemplate.id.asc())
        )
        return list(rows.all())

    async def find_by_id(self, template_id: int) -> DocumentTemplate | None:
        return await self.session.get(DocumentTemplate, template_id)

    async def find_limited_by_category(
        self,
        category: str,
        limit: int,
    ) -> Sequence[DocumentTemplate]:
        rows = await self.session.scalars(
            select(DocumentTemplate)
            .where(DocumentTemplate.status == "active", DocumentTemplate.category == category)
            .order_by(DocumentTemplate.id.asc())
            .limit(limit)
        )
        return rows.all()


class CasePlanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        plan_name: str,
        summary: str | None,
        case_profile: dict[str, Any],
        items: list[dict[str, Any]],
    ) -> CasePlan:
        plan = CasePlan(
            user_id=user_id,
            plan_name=plan_name,
            summary=summary,
            case_profile=case_profile,
            status="active",
        )
        self.session.add(plan)
        await self.session.flush()
        for i, it in enumerate(items, start=1):
            self.session.add(
                CasePlanItem(
                    plan_id=plan.id,
                    template_id=it["template_id"],
                    priority=i,
                    recommendation_reason=it.get("recommendation_reason"),
                    law_basis=it.get("law_basis"),
                    status="recommended",
                )
            )
        return plan


class GeneratedDocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
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
    ) -> GeneratedDocument:
        doc = GeneratedDocument(
            user_id=user_id,
            plan_id=plan_id,
            template_id=template_id,
            title=title,
            elements=elements,
            law_citations=law_citations,
            body_text=body_text,
            html=html,
            status="generated",
        )
        self.session.add(doc)
        return doc

    async def find_by_user(self, user_id: int) -> list[GeneratedDocument]:
        rows = await self.session.scalars(
            select(GeneratedDocument)
            .where(GeneratedDocument.user_id == user_id)
            .order_by(GeneratedDocument.updated_at.desc())
        )
        return list(rows.all())

    async def find_by_id(self, doc_id: UUID) -> GeneratedDocument | None:
        return await self.session.get(GeneratedDocument, doc_id)

    async def mark_downloaded(self, doc_id: UUID) -> None:
        await self.session.execute(
            GeneratedDocument.__table__.update()
            .where(GeneratedDocument.id == doc_id)
            .values(status="downloaded")
        )
