import requests
import time
import json
from datetime import datetime

import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration

from src.app.core.logger import get_logger
from src.app.core.config import settings

log = get_logger("sentry_service")


def sentry_to_loki(event, hint):
    """
    Converts a Sentry event to a format suitable for Loki and sends it there.

    :param event: The Sentry event
    :param hint: The Sentry event hint
    :return: The original event
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
            "Successfully sent event to Loki: %s",
            event.get("event_id"),
        )
    except Exception as e:
        log.error(
            "Failed to send to Loki: %s, error: %s",
            loki_url,
            str(e),
        )
    return event


def init_sentry():
    """
    Initialize Sentry SDK with the given DSN and settings.

    If `settings.sentry.dsn` is not set, the function will log an error and return.

    :param: None
    :return: None
    """
    dsn = settings.sentry.dsn
    if not dsn:
        log.error("Sentry DSN not configured, skipping initialization")
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
