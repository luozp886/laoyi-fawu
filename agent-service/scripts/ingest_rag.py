"""知识库构建脚本：遍历所有保险产品，将其条款PDF解析入库。

用法：
    cd D:\\heima\\hm-insurance\\agent-service
    uv run python scripts/ingest_rag.py
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import BM25BuiltInFunction, Milvus

from app.core.config import settings
from app.core.logging import get_logger
from app.infra.database import AsyncSessionFactory
from app.modules.product.service import ProductService
from app.rag.pipeline import RAGPipeline

logger = get_logger(__name__)


def build_vector_store() -> Milvus:
    """初始化 Embedding 模型与 Milvus VectorStore，返回已建好的向量库"""
    # 1.初始化向量模型
    embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    # 2.初始化 VectorStore，会自动创建 Collection
    vector_store = Milvus(
        embedding_function=embeddings,
        collection_name="insurance_collection",
        builtin_function=BM25BuiltInFunction(analyzer_params={"type": "chinese"}),
        vector_field=["dense", "sparse"],
        connection_args={"uri": settings.rag.milvus_url},
        auto_id=True,  # 自动生成id
    )
    return vector_store


async def list_all_products() -> list:
    """查询所有在售产品"""
    async with AsyncSessionFactory() as session:
        service = ProductService(session)
        return await service.list_products(category=None)


async def main() -> None:
    # 1.初始化向量库与 Pipeline
    vector_store = build_vector_store()
    pipeline = RAGPipeline(vector_store)
    # 2.查询所有产品
    products = await list_all_products()
    logger.info(f"共查询到 {len(products)} 个产品，开始构建知识库...")
    try:
        # 3.逐产品构建知识库
        for product in products:
            logger.info(f"开始构建产品: {product.name} ({product.clause_name})")
            await pipeline.ingest(product)
            logger.info(f"产品 {product.name} 知识库构建完成")
        logger.info("全部产品知识库构建完成")
    finally:
        pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
