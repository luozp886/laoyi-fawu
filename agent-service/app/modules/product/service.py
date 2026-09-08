from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.models import Product
from app.modules.product.repository import ProductRepository


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        # 创建repository对象
        self.repository = ProductRepository(session)

    async def list_products(self, category: str | None) -> list[Product]:
        # 调用repository查询
        return await self.repository.find_by_category(category)

    async def list_products_by_category(
        self,
        categories: list[str],
        premium_min: Decimal | None,
        limit_per_category: int,
    ) -> list[Product]:
        # 1.定义一个列表，保存所有的产品
        products: list[Product] = []
        # 2.遍历每个类别，不会重复
        # dict.fromkeys：把列表转成字典，key=列表项，值=None，由于字典天生key是唯一的，去重
        for category in dict.fromkeys(categories):
            # 3.调用repository查询每个类别的产品
            category_products = await self.repository.find_limited_by_category(
                category=category,
                premium_min=premium_min,
                limit=limit_per_category,
            )
            # 4.将查询到的产品合并到列表中
            products.extend(category_products)
        # 5.返回数据
        return products

    async def list_candidates(
        self,
        categories: list[str],
        premium_min: Decimal | None,
        limit_per_category: int,
    ) -> list[Product]:
        """按险种和最低保费条件查询可用于推荐的候选产品"""
        return await self.list_products_by_category(
            categories,
            premium_min,
            limit_per_category,
        )
