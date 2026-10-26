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
        """跨法规库检索；doc_id 为空表示全库检索。

        rerank（精排）由 Milvus 服务端调用阿里 dashscope 完成，依赖虚拟机/容器外网；
        一旦网络不可用会直接抛异常导致对话失败。这里做两级容错：
        优先带 rerank 检索，失败则降级为普通混合检索（稠密+稀疏），保证功能可用。
        """
        expr = f"doc_id == {doc_id}" if doc_id is not None else None

        try:
            child_chunks = await self.vector_store.asimilarity_search(
                query=query,
                k=k,
                fetch_k=10,
                expr=expr,
                reranker=create_reranker(query),
            )
        except Exception:
            # rerank 依赖 Milvus 容器访问外网（dashscope），网络不通时降级：
            # 去掉 reranker 重新检索，宁可排序稍差也不让对话报错。
            logger.warning("Milvus rerank 调用失败，已降级为普通混合检索", exc_info=True)
            child_chunks = await self.vector_store.asimilarity_search(
                query=query,
                k=k,
                fetch_k=10,
                expr=expr,
            )

        parent_ids = list(
            dict.fromkeys(
                child.metadata.get("parent_id")
                for child in child_chunks
                if child.metadata.get("parent_id")
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
