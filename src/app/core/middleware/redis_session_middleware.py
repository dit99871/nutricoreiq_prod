import json
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core.redis import redis_client
from src.app.utils.security import generate_redis_session_id, generate_csrf_token


class RedisSessionMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        session_id = request.cookies.get("redis_session_id")
        if not session_id:
            session_id = generate_redis_session_id()

        session_data = await redis_client.get(f"redis_session:{session_id}")
        if session_data:
            session = json.loads(session_data)
        else:
            session = {
                "redis_session_id": session_id,
                "csrf_token": generate_csrf_token(),
                "created_at": datetime.now().isoformat()
            }
        request.scope["redis_session"] = session

        response = await call_next(request)

        await redis_client.set(
            f"redis_session:{session_id}",
            json.dumps(session),
            ex=3600,
        )
        response.set_cookie(
            key="redis_session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="strict",
        )
        return response
