from decimal import Decimal
from typing import Any, Sequence, List

from sqlalchemy import select, ColumnElement  # 导入ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.models import Product

class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_category(
        self,
        category: str | None,
    ) -> list[Product]:
        # ✅显式声明：列表存放SQL布尔条件对象
        conditions: List[ColumnElement[bool]] = [Product.status == "active"]
        if category:
            conditions.append(Product.category == category)

        products = await self.session.scalars(
            select(Product)
            .where(*conditions)
            .order_by(Product.id.asc())
        )
        return list(products.all())

    async def find_by_id(self, product_id: int) -> Product | None:
        # 按主键查询单个产品
        return await self.session.get(Product, product_id)

    async def find_limited_by_category(
        self,
        category: str,
        premium_min: Decimal | None,
        limit: int,
    ) -> Sequence[Any]:
        # ✅同样加上类型注解
        conditions: List[ColumnElement[bool]] = [
            Product.status == "active",
            Product.category == category,
        ]
        if premium_min is not None:
            conditions.append(Product.min_premium < premium_min)

        products = await self.session.scalars(
            select(Product)
            .where(*conditions)
            .order_by(
                Product.min_premium.asc().nullslast(),
                Product.id.asc(),
            )
            .limit(limit)
        )
        return products.all()