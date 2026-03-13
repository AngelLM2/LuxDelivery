from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.category import CategoryRepository
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.cache_service import CacheService

class ProductService:
    def __init__(self, session: AsyncSession):
        self.repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)
        self.cache = CacheService
        self.ttl = settings.TTL_PRODUCTS_LIST

    async def create(self, data: ProductCreate):
        if await self.repo.search_name(data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Produto ja existe.",
            )
        if data.category_id and not await self.category_repo.search_id(data.category_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria nao encontrada.",
            )
        product = await self.repo.create(
            name=data.name,
            price=data.price,
            description=data.description,
            is_offer=data.is_offer,
            category_id=data.category_id,
        )
        await self.cache.delete_pattern("products:list:*")
        return product

    async def list(self, limit: int = 10, cursor: int = 0):
        if limit < 1 or limit > settings.PRODUCTS_MAX_PAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"limit deve estar entre 1 e {settings.PRODUCTS_MAX_PAGE_SIZE}.",
            )
        if cursor < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cursor deve ser maior ou igual a 0.",
            )

        key = self.cache.key_products_list(cursor, limit)
        cached = await self.cache.get(key)
        if cached is not None:
            return cached

        product = await self.repo.list(limit=limit, cursor=cursor)
        payload = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "is_offer": c.is_offer,
                "price": c.price,
                "category_id": c.category_id,
            }
            for c in product
        ]
        await self.cache.set(key, payload, self.ttl)
        return payload



    async def delete(self, product_id: int):
        deleted = await self.repo.delete(product_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nao encontrado.",
            )
        await self.cache.delete_pattern("products:list:*")
        return {"message": f"Produto {product_id} removido com sucesso."}

    async def update(self, product_id: int, data: ProductUpdate):
        payload = data.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo enviado para atualizacao.",
            )
        if "category_id" in payload and payload["category_id"] is not None:
            if not await self.category_repo.search_id(payload["category_id"]):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Categoria nao encontrada.",
                )
        updated = await self.repo.update(product_id, payload)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nao encontrado.",
            )
        await self.cache.delete_pattern("products:list:*")
        return updated
