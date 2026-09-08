"""RAG 知识库构建。

与保险版（MinerU 解析 PDF + 大模型优化）不同，法规是直接可用 .md 文本，
因此这里只做“按 Markdown 标题切父块 + 递归切子块”，再分别落 Milvus 与 PostgreSQL。
"""
from __future__ import annotations

from uuid import uuid4

from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.core.logging import get_logger
from app.infra.database import AsyncSessionFactory
from app.rag.models import KnowledgeChunk
from app.rag.repository import KnowledgeChunkRepository

logger = get_logger(__name__)


class RAGPipeline:
    def __init__(self, vector_store: Milvus) -> None:
        self._vector_store = vector_store
        self._markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4"),
            ],
            strip_headers=True,
        )
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "；", ";", "，", ","],
            keep_separator="end",
        )
        logger.info("RAG Pipeline 初始化完成")

    async def ingest_document(self, *, doc_id: int, doc_title: str, markdown: str) -> None:
        """入库某部法规：切父块/子块 → 子块进 Milvus → 父块进 PostgreSQL。"""
        parent_chunks, child_chunks = self._chunk(doc_id=doc_id, doc_title=doc_title, markdown=markdown)

        self._save_child_chunks(doc_id, child_chunks)
        await self._save_parent_chunks(doc_id, parent_chunks)

    def _chunk(
        self,
        *,
        doc_id: int,
        doc_title: str,
        markdown: str,
    ) -> tuple[list[KnowledgeChunk], list[Document]]:
        sections = self._markdown_splitter.split_text(markdown)
        parent_chunks: list[KnowledgeChunk] = []
        child_chunks: list[Document] = []

        for section in sections:
            section_path = list(section.metadata.values())
            parent = KnowledgeChunk(
                id=uuid4(),
                doc_id=doc_id,
                doc_title=doc_title,
                section_path=section_path,
                content=section.page_content,
            )
            parent_chunks.append(parent)

            section.metadata = {
                "doc_id": doc_id,
                "parent_id": str(parent.id),
            }
            children = self._child_splitter.split_documents([section])
            header = "\n".join(section_path) + "\n"
            for child in children:
                child.page_content = header + child.page_content
            child_chunks.extend(children)

        return parent_chunks, child_chunks

    def _save_child_chunks(self, doc_id: int, child_chunks: list[Document]) -> None:
        if self._vector_store.client.has_collection(self._vector_store.collection_name):
            self._vector_store.delete(expr=f"doc_id == {doc_id}")
        self._vector_store.add_documents(child_chunks)

    async def _save_parent_chunks(self, doc_id: int, parent_chunks: list[KnowledgeChunk]) -> None:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                repository = KnowledgeChunkRepository(session)
                await repository.delete_by_doc_id(doc_id)
                repository.add_all(parent_chunks)

    def close(self) -> None:
        logger.info("RAG Pipeline 关闭")
