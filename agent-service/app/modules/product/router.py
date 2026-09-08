from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_session
from app.modules.product.schemas import ProductResponse
from app.modules.product.service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])

async def get_product_service(
    session: AsyncSession = Depends(get_session),
) -> ProductService:
    return ProductService(session)

@router.get("", response_model=list[ProductResponse])
async def list_products(
    category: str | None = None,
    service: ProductService = Depends(get_product_service),
) -> list[ProductResponse]:
    # 1.调用service查询
    return await service.list_products(category)

@router.get("/candidates", response_model=list[ProductResponse])
async def list_candidates(
    # Query：声明这个参数是从查询字符串中取（URL地址中 ?参数名=值），并帮我校验
    categories: list[str] = Query(min_length=1),
    premium_min: Decimal | None = None,
    # lt=less than 小于，gt=greater than 大于；1 < limit_per_category < 10，校验不通过返回状态码422
    limit_per_category: int = Query(gt=1, lt=10),
    service: ProductService = Depends(get_product_service),
) -> list[ProductResponse]:
    # 1.调用service查询
    products = await service.list_products_by_category(
        categories,
        premium_min,
        limit_per_category,
    )
    # 2.返回结果
    return products