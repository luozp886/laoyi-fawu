from uuid import UUID

from sqlalchemy import ARRAY, BigInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin


class KnowledgeChunk(Base, CreateAtMixin):
    """父知识块（RAG），以“知识文档 doc_id”为粒度（某部法律法规）"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    doc_id: Mapped[int] = mapped_column(BigInteger)
    doc_title: Mapped[str] = mapped_column(String(300))
    section_path: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
    )
    content: Mapped[str] = mapped_column(Text)
