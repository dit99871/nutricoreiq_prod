import json
import time
from datetime import datetime

import requests
import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("sentry_service")


def sentry_to_loki(event, hint):
    """
    Конвертирует Sentry событие в формат, подходящий для Loki, и отправляет его туда.

    :param event: Sentry событие
    :param hint: Подсказка Sentry события
    :return: Исходное событие
    """
    loki_url = settings.loki.url
    log_entry = {
        "streams": [
            {
                "stream": {
                    "source": "sentry",
                    "level": event.get("level", "error"),
                    "app": "fastapi",
                },
                "values": [
                    [
                        str(int(time.time() * 1e9)),
                        json.dumps(
                            {
                                "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[
                                    :-3
                                ],
                                "message": event.get("message", "Sentry event"),
                                "event_id": event.get("event_id"),
                            }
                        ),
                    ]
                ],
            }
        ]
    }
    try:
        response = requests.post(loki_url, json=log_entry)
        response.raise_for_status()  # вызывает исключение при http-ошибке
        log.info(
            "Успешно отправлено в Loki: %s",
            event.get("event_id"),
        )
    except Exception as e:
        log.error(
            "Ошибка при отправлении в Loki: %s, error: %s",
            loki_url,
            str(e),
        )
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
