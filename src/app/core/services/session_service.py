import json
from datetime import datetime
from typing import Optional

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.redis import redis_client
from src.app.core.utils.security import generate_csrf_token

logger = get_logger("session_service")


class SessionService:
    """Сервис для управления сессиями"""

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Получает сессию из Redis"""

        session_data = await redis_client.get(f"redis_session:{session_id}")
        if session_data:
            return json.loads(session_data)
        return None

    async def save_session(self, session_id: str, session: dict) -> bool:
        """Сохраняет сессию в Redis"""

        try:
            await redis_client.set(
                f"redis_session:{session_id}",
                json.dumps(session),
                ex=settings.redis.session_ttl,
            )
            logger.debug("Сессия %s успешно сохранена в Redis", session_id)
            return True

        except Exception as e:
            logger.error("Ошибка при сохранении сессии %s в Redis: %s", session_id, e)
            return False

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
