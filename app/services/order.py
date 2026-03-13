from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.repositories.notification import NotificationRepository
from app.repositories.order import OrderRepository
from app.repositories.product import ProductRepository
from app.schemas.order import OrderCreate, OrderStatusUpdate

DEFAULT_STATUS_DESCRIPTIONS = {
    OrderStatus.CREATED: "Pedido criado.",
    OrderStatus.CONFIRMED: "Pedido confirmado.",
    OrderStatus.PREPARING: "Pedido em preparo.",
    OrderStatus.OUT_FOR_DELIVERY: "Pedido saiu para entrega.",
    OrderStatus.DELIVERED: "Pedido entregue.",
    OrderStatus.CANCELED: "Pedido cancelado.",
}

ALLOWED_TRANSITIONS = {
    OrderStatus.CREATED: {OrderStatus.CONFIRMED, OrderStatus.CANCELED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELED},
    OrderStatus.PREPARING: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELED},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.CANCELED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELED: set(),
}


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)
        self.notification_repo = NotificationRepository(session)

    async def create(self, current_user: User, data: OrderCreate):
        if current_user.role not in {UserRole.CUSTOMER, UserRole.ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas cliente/admin podem criar pedidos.",
            )
        try:
            items_payload: list[tuple[int, int, float]] = []
            total_amount = 0.0
            for item in data.items:
                product = await self.product_repo.search_id(item.product_id)
                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Produto {item.product_id} nao encontrado.",
                    )
                items_payload.append((product.id, item.quantity, product.price))
                total_amount += item.quantity * product.price
            order = await self.order_repo.create(
                customer_id=current_user.id,
                delivery_address=data.delivery_address,
                notes=data.notes,
            )
            for product_id, quantity, unit_price in items_payload:
                await self.order_repo.add_item(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                )
            order.total_amount = total_amount
            await self.order_repo.add_tracking_event(
                order_id=order.id,
                status=OrderStatus.CREATED,
                description=DEFAULT_STATUS_DESCRIPTIONS[OrderStatus.CREATED],
                created_by_user_id=current_user.id,
            )
            await self.notification_repo.create(
                user_id=current_user.id,
                order_id=order.id,
                event_type="order_created",
                message=f"Pedido #{order.id} criado com sucesso.",
            )
            await self.order_repo.commit()
            return await self.order_repo.search_by_id(order.id)
        except HTTPException:
            await self.order_repo.rollback()
            raise
        except Exception:
            await self.order_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar pedido.",
            )

    async def get_by_id(self, order_id: int, current_user: User):
        order = await self.order_repo.search_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido nao encontrado.")
        self._ensure_access(order, current_user)
        return order

    async def list_for_user(self, current_user: User):
        if current_user.role == UserRole.ADMIN:
            return await self.order_repo.list_all()
        if current_user.role == UserRole.CUSTOMER:
            return await self.order_repo.list_for_user(current_user.id, current_user.role.value)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissao para listar pedidos.",
        )

    async def update_status(self, order_id: int, data: OrderStatusUpdate, current_user: User):
        order = await self.order_repo.search_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido nao encontrado.")

        self._ensure_can_change_status(order, data.status, current_user)
        self._ensure_valid_transition(order.status, data.status)

        order.status = data.status
        self._set_status_timestamp(order, data.status)
        description = data.description or DEFAULT_STATUS_DESCRIPTIONS[data.status]
        await self.order_repo.add_tracking_event(
            order_id=order.id,
            status=data.status,
            description=description,
            created_by_user_id=current_user.id,
        )

        await self.notification_repo.create(
            user_id=order.customer_id,
            order_id=order.id,
            event_type=f"order_{data.status.value}",
            message=f"Pedido #{order.id} agora esta '{data.status.value}'.",
        )

        await self.order_repo.commit()
        return await self.order_repo.search_by_id(order.id)

    async def tracking(self, order_id: int, current_user: User):
        order = await self.get_by_id(order_id, current_user)
        return order.tracking_events

    def _ensure_access(self, order, current_user: User):
        if current_user.role == UserRole.ADMIN:
            return
        if current_user.role == UserRole.CUSTOMER and order.customer_id == current_user.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissao para acessar este pedido.",
        )

    def _ensure_valid_transition(self, old_status: OrderStatus, new_status: OrderStatus):
        if old_status == new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pedido ja esta neste status.",
            )
        if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transicao invalida: {old_status.value} -> {new_status.value}.",
            )

    def _ensure_can_change_status(self, order, new_status: OrderStatus, current_user: User):
        if current_user.role == UserRole.ADMIN:
            return
        if current_user.role == UserRole.CUSTOMER:
            if order.customer_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Pedido nao pertence ao cliente autenticado.",
                )
            if new_status != OrderStatus.CANCELED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cliente so pode cancelar pedido.",
                )
            if order.status not in {OrderStatus.CREATED, OrderStatus.CONFIRMED}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pedido nao pode mais ser cancelado pelo cliente.",
                )

    def _set_status_timestamp(self, order, new_status: OrderStatus):
        now = datetime.now(timezone.utc)
        if new_status == OrderStatus.CONFIRMED:
            order.confirmed_at = now
        elif new_status == OrderStatus.PREPARING:
            order.preparing_at = now
        elif new_status == OrderStatus.OUT_FOR_DELIVERY:
            order.out_for_delivery_at = now
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = now
        elif new_status == OrderStatus.CANCELED:
            order.canceled_at = now
