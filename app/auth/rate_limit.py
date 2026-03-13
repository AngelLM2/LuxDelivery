import time
import logging
from uuid import uuid4
from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError
from app.core.redis_client import get_redis
from app.config import settings

logger = logging.getLogger(__name__)


async def enforce_auth_rate_limit(request: Request) -> None:
    
    try:
        r = await get_redis()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        key = f"rate:{request.url.path}:{client_ip}"
        window  = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
        max_req = settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS
        now     = time.time()
        cutoff  = now - window

        async with r.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            member = f"{now}:{uuid4().hex}"
            pipe.zadd(key, {member: now})
            pipe.expire(key, window)
            results = await pipe.execute()

        count = results[1]

        if count >= max_req:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas. Tente novamente em instantes.",
                headers={"Retry-After": str(window)},
            )

    except HTTPException:
        raise
    except RedisError as e:

        logger.error("Rate limiter Redis indisponível: %s", e)
