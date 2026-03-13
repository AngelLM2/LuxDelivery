from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_roles
from app.config import settings
from app.database import get_session
from app.models.user import UserRole
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductRead], status_code=status.HTTP_200_OK)
async def list_products(
    limit: int = Query(default=20, ge=1, le=settings.PRODUCTS_MAX_PAGE_SIZE),
    cursor: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    _current_user=Depends(get_current_user),
):
    service = ProductService(session)
    return await service.list(limit=limit, cursor=cursor)


@router.post(
    "/",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
):
    service = ProductService(session)
    return await service.create(data)


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = ProductService(session)
    return await service.update(product_id, data)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ProductService(session)
    return await service.delete(product_id)
