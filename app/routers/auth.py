from fastapi import APIRouter, Depends, Header, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rate_limit import enforce_auth_rate_limit
from app.database import get_session
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(data: UserCreate, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    return await service.register(data)


@router.post(
    "/bootstrap-admin",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def bootstrap_admin(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
    bootstrap_token: str | None = Header(default=None, alias="X-Bootstrap-Token"),
):
    service = AuthService(session)
    return await service.bootstrap_admin(data, bootstrap_token)


@router.post(
    "/login",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    return await service.login(data)


@router.post(
    "/token",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    data = LoginRequest(email=form_data.username, password=form_data.password)
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def refresh_token(data: RefreshTokenRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    return await service.refresh(data.refresh_token)


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
async def who_am_i(current_user=Depends(get_current_user)):
    return current_user
