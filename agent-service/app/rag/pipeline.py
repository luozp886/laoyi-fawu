"""RAG 知识库构建。

与保险版（MinerU 解析 PDF + 大模型优化）不同，法规是直接可用 .md 文本，
因此这里只做“按条文切块（第X条）”，再分别落 Milvus 与 PostgreSQL。
"""
from __future__ import annotations

import re
from uuid import uuid4

from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.logging import get_logger
from app.infra.database import AsyncSessionFactory
from app.rag.models import KnowledgeChunk
from app.rag.repository import KnowledgeChunkRepository

logger = get_logger(__name__)

_CLAUSE_RE = re.compile(r"^\s*(第[一二三四五六七八九十百零〇0-9]+条)")
_HEADER_RE = re.compile(r"^(#{1,4})\s+(.+)$")


class RAGPipeline:
    def __init__(self, vector_store: Milvus) -> None:
        self._vector_store = vector_store
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "；", ";", "，", ","],
            keep_separator="end",
        )
        logger.info("RAG Pipeline 初始化完成")

    async def ingest_document(self, *, doc_id: int, doc_title: str, markdown: str) -> None:
        """入库某部法规：按条文切块 → 子块进 Milvus → 父块进 PostgreSQL。"""
        parent_chunks, child_chunks = self._chunk(doc_id=doc_id, doc_title=doc_title, markdown=markdown)

        self._save_child_chunks(doc_id, child_chunks)
        await self._save_parent_chunks(doc_id, parent_chunks)

    def _split_clause_sections(self, markdown: str) -> list[tuple[list[str], str]]:
        """按“第X条”切分法规文本，返回 [(章节路径, 条文正文)]。

        章节路径由 Markdown 标题维护（法律名/章/节），条文正文保留“第X条”标题行。
        """
        sections: list[tuple[list[str], str]] = []
        path: list[str] = []
        buf: list[str] = []
        buf_path: list[str] = []

        def flush() -> None:
            if buf:
                sections.append((list(buf_path), "\n".join(buf).strip()))
                buf.clear()

        for raw_line in markdown.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                buf.append("")
                continue
            header = _HEADER_RE.match(stripped)
            if header:
                flush()
                level = len(header.group(1))
                title = header.group(2).strip()
                path = path[: level - 1] + [title]
                buf_path = list(path)
                continue
            if _CLAUSE_RE.match(stripped):
                flush()
                buf_path = list(path)
            buf.append(stripped)
        flush()
        return sections

    def _chunk(
        self,
        *,
        doc_id: int,
        doc_title: str,
        markdown: str,
    ) -> tuple[list[KnowledgeChunk], list[Document]]:
        sections = self._split_clause_sections(markdown)
        parent_chunks: list[KnowledgeChunk] = []
        child_chunks: list[Document] = []

        for section_path, text in sections:
            if not text:
                continue
            parent = KnowledgeChunk(
                id=uuid4(),
                doc_id=doc_id,
                doc_title=doc_title,
                section_path=section_path,
                content=text,
            )
            parent_chunks.append(parent)

            # 条文级入库；超长条文（如整条含多款）再递归切子块
            if len(text) <= 700:
                children = [
                    Document(
                        page_content=text,
                        metadata={"doc_id": doc_id, "parent_id": str(parent.id)},
                    )
                ]
            else:
                tmp = Document(page_content=text, metadata={})
                children = self._child_splitter.split_documents([tmp])
                header = "\n".join(section_path) + "\n"
                for child in children:
                    child.page_content = header + child.page_content
                    child.metadata = {"doc_id": doc_id, "parent_id": str(parent.id)}
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

    async def remove_document(self, doc_id: int) -> None:
        """从知识库中移除某文档：先删 Milvus 子块向量，再删 PostgreSQL 父块。"""
        if self._vector_store.client.has_collection(self._vector_store.collection_name):
            self._vector_store.delete(expr=f"doc_id == {doc_id}")
        async with AsyncSessionFactory() as session:
            async with session.begin():
                await KnowledgeChunkRepository(session).delete_by_doc_id(doc_id)
        logger.info("已从知识库移除文档 doc_id=%s", doc_id)

    def close(self) -> None:
        logger.info("RAG Pipeline 关闭")
