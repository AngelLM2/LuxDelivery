from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.redis_client import close_redis, get_redis
from app.middleware.rate_limit import rate_limit_middleware
from app.database import Base, engine
from app.routers import (
    analytics_router,
    auth_router,
    category_router,
    notification_router,
    order_router,
    product_router,
    user_router,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        r = await get_redis()
        await r.ping()
        logger.info("Redis conectado com sucesso.")
    except Exception as exc:
        logger.warning("Redis indisponivel no startup: %s", exc)
    yield
    try:
        await close_redis()
    except Exception as exc:
        logger.warning("Falha ao fechar Redis: %s", exc)
    try:
        await engine.dispose()
    except Exception as exc:
        logger.warning("Falha ao fechar engine do banco: %s", exc)


app = FastAPI(title="Lux Delivery API", version="1.0.0", lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "https://meusite.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.middleware("http")(rate_limit_middleware)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(product_router)
app.include_router(category_router)
app.include_router(order_router)
app.include_router(notification_router)
app.include_router(analytics_router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok"}
