from langchain_milvus import Milvus
from pymilvus import Function, FunctionType

from app.core.logging import get_logger
from app.infra.database import AsyncSessionFactory
from app.rag.models import KnowledgeChunk
from app.rag.repository import KnowledgeChunkRepository

logger = get_logger(__name__)


def create_reranker(query: str) -> Function:
    """milvus reranker（阿里 gte-rerank-v2）"""
    return Function(
        name="dashscope_semantic_ranker",
        input_field_names=["text"],
        function_type=FunctionType.RERANK,
        params={
            "reranker": "model",
            "provider": "ali",
            "model_name": "gte-rerank-v2",
            "queries": [query],
            "max_client_batch_size": 5,
        },
    )


class KnowledgeRetriever:

    def __init__(self, vector_store: Milvus):
        self.vector_store = vector_store
        logger.info("RAG Retriever 初始化完成")

    async def retrieve(
        self,
        query: str,
        k: int,
        doc_id: int | None = None,
    ) -> list[KnowledgeChunk]:
        """跨法规库检索；doc_id 为空表示全库检索。"""
        expr = f"doc_id == {doc_id}" if doc_id is not None else None

        child_chunks = await self.vector_store.asimilarity_search(
            query=query,
            k=k,
            fetch_k=10,
            expr=expr,
            reranker=create_reranker(query),
        )

        parent_ids = list(
            dict.fromkeys(
                child.metadata["parent_id"] for child in child_chunks
            )
        )
        if not parent_ids:
            return []

        async with AsyncSessionFactory() as session:
            repository = KnowledgeChunkRepository(session)
            parent_chunks = await repository.list_by_ids(parent_ids)

        parent_map = {str(parent.id): parent for parent in parent_chunks}
        return [
            parent_map[parent_id]
            for parent_id in parent_ids
            if parent_id in parent_map
        ]
