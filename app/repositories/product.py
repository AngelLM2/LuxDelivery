from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str, price: float, description: str, is_offer: bool, category_id: int | None) -> Product:
        product = Product(
            name=name,
            price=price,
            description=description,
            is_offer=is_offer,
            category_id=category_id,
        )
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def search_name(self, product_name: str) -> Product | None:
        result = await self.session.execute(select(Product).filter(Product.name == product_name))
        return result.scalars().first()

    async def search_id(self, product_id: int) -> Product | None:
        result = await self.session.execute(select(Product).filter(Product.id == product_id))
        return result.scalars().first()

    async def list(self, limit: int = 10, cursor: int = 0) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .filter(Product.id > cursor)
            .order_by(Product.id.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def delete(self, product_id: int) -> Product | None:
        product = await self.search_id(product_id)
        if not product:
            return None
        await self.session.delete(product)
        await self.session.commit()
        return product

    async def update(self, product_id: int, data: dict) -> Product | None:
        product = await self.search_id(product_id)
        if not product:
            return None

        for key, value in data.items():
            setattr(product, key, value)

        await self.session.commit()
        await self.session.refresh(product)
        return product
