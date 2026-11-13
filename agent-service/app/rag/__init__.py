from dotenv import load_dotenv
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import BM25BuiltInFunction, Milvus

from app.core.config import settings
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import KnowledgeRetriever

# 提前加载 .env，确保 DashScopeEmbeddings 能读取 DASHSCOPE_API_KEY
load_dotenv()

_embeddings = DashScopeEmbeddings(model="text-embedding-v4")

_vector_store = Milvus(
    embedding_function=_embeddings,
    collection_name="legal_collection",
    builtin_function=BM25BuiltInFunction(analyzer_params={"type": "chinese"}),
    vector_field=["dense", "sparse"],
    connection_args={"uri": settings.rag.milvus_url},
    auto_id=True,
)

pipeline = RAGPipeline(_vector_store)
retriever = KnowledgeRetriever(_vector_store)


def close_rag() -> None:
    pipeline.close()
    _vector_store.client.close()


__all__ = ["pipeline", "retriever", "close_rag"]
