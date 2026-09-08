"""劳动法规 RAG 入库脚本：读取 data/legal/*.md 法规文本，构建知识库。

用法：
    cd agent-service
    uv run python scripts/ingest_rag.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import BM25BuiltInFunction, Milvus

from app.core.config import APP_ROOT, settings
from app.core.logging import get_logger
from app.rag.pipeline import RAGPipeline

logger = get_logger(__name__)

# 法规清单：doc_id 稳定编号，title 与文件名对应。文件须放在 data/legal/ 下。
LEGAL_DIR = APP_ROOT / "data" / "legal"
LAW_CORPUS: list[dict[str, str]] = [
    {"id": "1", "title": "中华人民共和国劳动法", "file": "labor_law.md"},
    {"id": "2", "title": "中华人民共和国劳动合同法", "file": "labor_contract_law.md"},
    {"id": "3", "title": "中华人民共和国劳动争议调解仲裁法", "file": "labor_dispute_arbitration_law.md"},
    {"id": "4", "title": "工伤保险条例", "file": "work_injury_regulation.md"},
]


def build_vector_store() -> Milvus:
    embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    return Milvus(
        embedding_function=embeddings,
        collection_name="legal_collection",
        builtin_function=BM25BuiltInFunction(analyzer_params={"type": "chinese"}),
        vector_field=["dense", "sparse"],
        connection_args={"uri": settings.rag.milvus_url},
        auto_id=True,
    )


async def main() -> None:
    vector_store = build_vector_store()
    pipeline = RAGPipeline(vector_store)
    logger.info(f"知识目录: {LEGAL_DIR}")
    try:
        for item in LAW_CORPUS:
            path = LEGAL_DIR / item["file"]
            if not path.exists():
                logger.warning(f"未找到法规文件: {path}")
                continue
            markdown = path.read_text(encoding="utf-8")
            logger.info(f"开始构建: {item['title']}")
            await pipeline.ingest_document(
                doc_id=int(item["id"]),
                doc_title=item["title"],
                markdown=markdown,
            )
            logger.info(f"{item['title']} 构建完成")
        logger.info("全部法规知识库构建完成")
    finally:
        pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
