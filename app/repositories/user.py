from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.models.user import UserRole
from app.models.user import User


class UserRepository:
    BOOTSTRAP_ADMIN_LOCK_ID = 824311

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        full_name: str,
        email: str,
        phone: str | None,
        hashed_password: str,
        role,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            hashed_password=hashed_password,
            role=role,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def search_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    async def search_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def search_by_phone(self, phone: str) -> User | None:
        result = await self.session.execute(select(User).filter(User.phone == phone))
        return result.scalars().first()

    async def list(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.id.asc()))
        return result.scalars().all()

    async def admin_exists(self) -> bool:
        result = await self.session.execute(
            select(User.id).filter(User.role == UserRole.ADMIN).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def update(self, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def lock_bootstrap_admin(self) -> None:
        bind = self.session.bind
        if bind and bind.dialect.name == "postgresql":
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": self.BOOTSTRAP_ADMIN_LOCK_ID},
            )
