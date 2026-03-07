import json
import time
from datetime import datetime
from typing import Optional

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.redis import redis_client
from src.app.core.utils.security import generate_csrf_token

logger = get_logger("session_service")


class SessionService:
    """Сервис для управления сессиями"""

    def __init__(self):
        self._session_cache: dict[str, dict] = {}
        self._cache_ttl = 300  # 5 минут

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Получает сессию с кешированием"""

        # проверяем кеш
        if session_id in self._session_cache:
            cached_data = self._session_cache[session_id]
            if time.time() - cached_data["cached_at"] < self._cache_ttl:
                return cached_data["session"]

        session_data = await redis_client.get(f"redis_session:{session_id}")

        if session_data:
            session = json.loads(session_data)
            # кешируем
            self._session_cache[session_id] = {
                "session": session,
                "cached_at": time.time(),
            }
            return session

        return None

    async def save_session(self, session_id: str, session: dict) -> None:
        """Сохраняет сессию в Redis и кеше"""

        await redis_client.set(
            f"redis_session:{session_id}",
            json.dumps(session),
            ex=settings.redis.session_ttl,
        )

        # Обновляем кеш
        self._session_cache[session_id] = {
            "session": session,
            "cached_at": time.time(),
        }

    def create_new_session(self, session_id: str) -> dict:
        """Создает новую сессию"""

        return {
            "redis_session_id": session_id,
            "created_at": datetime.now().isoformat(),
        }

    def ensure_csrf_token(self, session: dict) -> str:
        """Обеспечивает наличие CSRF токена в сессии"""

        csrf_token = session.get("csrf_token") or generate_csrf_token()
        session["csrf_token"] = csrf_token

        return csrf_token


session_service = SessionService()
