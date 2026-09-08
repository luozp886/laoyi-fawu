from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, BigInteger, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin, UpdateAtMixin


class DocumentTemplate(Base, CreateAtMixin, UpdateAtMixin):
    """法律文书模板（咨询平台的“商品/产品”）"""

    __tablename__ = "document_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    doc_type: Mapped[str | None] = mapped_column(String(80))
    source_note: Mapped[str | None] = mapped_column(String(300))
    image_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    target_scenario: Mapped[str | None] = mapped_column(String(500))
    template_key: Mapped[str] = mapped_column(String(120), unique=True)
    element_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    highlights: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        default=list,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        server_default="active",
    )


class CasePlan(Base, CreateAtMixin, UpdateAtMixin):
    """维权处理方案（顾问根据案情给出的行动/文书建议组合）"""

    __tablename__ = "case_plans"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    plan_name: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str | None] = mapped_column(Text)
    case_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        server_default="draft",
    )


class CasePlanItem(Base, CreateAtMixin, UpdateAtMixin):
    """维权方案项：推荐某份文书模板 + 理由 + 依据"""

    __tablename__ = "case_plan_items"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("case_plans.id", ondelete="CASCADE"),
    )
    template_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_templates.id"),
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    recommendation_reason: Mapped[str | None] = mapped_column(Text)
    law_basis: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30),
        default="recommended",
        server_default="recommended",
    )


class GeneratedDocument(Base, CreateAtMixin, UpdateAtMixin):
    """生成的法律文书成品（用户填要素拼装后的结果）"""

    __tablename__ = "generated_documents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    plan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("case_plans.id"),
    )
    template_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_templates.id"),
    )
    title: Mapped[str] = mapped_column(String(200))
    elements: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    law_citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    body_text: Mapped[str | None] = mapped_column(Text)
    html: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30),
        default="generated",
        server_default="generated",
    )
