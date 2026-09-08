from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentTemplateResponse(BaseModel):
    """法律文书模板（浏览页卡片 / 详情）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    doc_type: str | None = None
    source_note: str | None = None
    image_url: str | None = None
    description: str | None = None
    target_scenario: str | None = None
    template_key: str
    element_schema: dict[str, Any] = Field(default_factory=dict)
    highlights: list[str] | None = None
    status: str


class GeneratedDocumentResponse(BaseModel):
    """已生成的法律文书"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    plan_id: UUID | None = None
    template_id: int
    title: str
    elements: dict[str, Any] = Field(default_factory=dict)
    law_citations: list[dict[str, Any]] = Field(default_factory=list)
    body_text: str | None = None
    html: str | None = None
    status: str
    created_at: Any = None
    updated_at: Any = None


class GeneratedDocumentListResponse(BaseModel):
    """我的文书列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: int
    title: str
    template_name: str | None = None
    status: str
    created_at: Any = None
