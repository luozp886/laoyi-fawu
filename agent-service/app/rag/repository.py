from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.models import KnowledgeChunk


class KnowledgeChunkRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_by_doc_id(self, doc_id: int) -> None:
        await self.session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc_id)
        )

    def add_all(self, chunks: list[KnowledgeChunk]) -> None:
        self.session.add_all(chunks)

    async def list_by_ids(self, ids: list[str]) -> list[KnowledgeChunk]:
        result = await self.session.scalars(
            select(KnowledgeChunk).where(KnowledgeChunk.id.in_(ids))
        )
        return result.all()
