"""Сервис для инициализации Sentry SDK."""

import asyncio
import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("sentry_service")


def sentry_to_loki(event, hint):
    """
    Обработчик события, который отправляет его в Loki.
    """
    try:
        # импортируем локально, чтобы избежать циклических импортов
        from src.app.core.tasks import send_event_to_loki

        # записываем событие в очередь для отправки в Loki
        asyncio.get_running_loop().create_task(
            send_event_to_loki.kiq(
                event_id=event.get("event_id"),
                message=event.get("message", "Sentry event"),
                level=event.get("level", "error"),
            )
        )
        log.info("Событие поставлено в очередь Loki: %s", event.get("event_id"))

    except RuntimeError:
        # на случай вызова вне асинк-контекста (например, в тестах)
        log.warning(
            "Event loop не запущен, событие Loki пропущено: %s", event.get("event_id")
        )

    except Exception as e:
        log.error("Ошибка постановки в очередь Loki: %s", e)

    return event


def init_sentry():
    """
    Инициализирует Sentry SDK с указанным DSN и настройками.

    Если `settings.sentry.dsn` не установлен, функция запишет ошибку в лог и вернет управление.
    """
    dsn = settings.sentry.dsn
    if not dsn:
        log.error("Sentry DSN не сконфигурирован, пропускаем инициализацию")
        return

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=1.0,  # мониторинг производительности
        environment="production",
        release="1.0.0",
        profile_session_sample_rate=0.1,  # мониторинг профилей
        profile_lifecycle="trace",
        send_default_pii=False,  # отправка персональных данных
        before_send=sentry_to_loki,  # вебхук для loki
        integrations=[
            StarletteIntegration(
                transaction_style="endpoint",
                middleware_spans=False,
            ),
        ],
    )
