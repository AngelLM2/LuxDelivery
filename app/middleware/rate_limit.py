import logging
import time
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from app.auth.jwt import decode_token
from app.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _get_user_id_from_auth(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return str(user_id)


def _rate_limit_response(window: int) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Muitas requisicoes. Tente novamente em instantes."},
        headers={"Retry-After": str(window)},
    )


async def rate_limit_middleware(request: Request, call_next):
    try:
        r = await get_redis()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        max_per_ip = settings.RATE_LIMIT_MAX_PER_IP
        max_per_user = settings.RATE_LIMIT_MAX_PER_USER

        now = time.time()
        cutoff = now - window

        client_ip = _get_client_ip(request)
        user_id = _get_user_id_from_auth(request)

        keys: list[tuple[str, int]] = [(f"rate:ip:{client_ip}", max_per_ip)]
        if user_id:
            keys.append((f"rate:user:{user_id}", max_per_user))

        async with r.pipeline(transaction=True) as pipe:
            for key, _ in keys:
                pipe.zremrangebyscore(key, 0, cutoff)
                pipe.zcard(key)
                member = f"{now}:{uuid4().hex}"
                pipe.zadd(key, {member: now})
                pipe.expire(key, window)
            results = await pipe.execute()

        for idx, (_, limit) in enumerate(keys):
            count = results[idx * 4 + 1]
            if count >= limit:
                return _rate_limit_response(window)

    except RedisError as e:
        logger.error("Rate limiter Redis indisponivel: %s", e)

    return await call_next(request)
