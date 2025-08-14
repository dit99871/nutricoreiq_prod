import requests
import time
import json
from datetime import datetime

import sentry_sdk

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
        requests.post(loki_url, json=log_entry)
    except Exception as e:
        log.error(
            "Failed to send to Loki: %s, error: %s",
            loki_url,
            str(e),
        )
    return event


def init_sentry():
    """
    Initializes the Sentry SDK with configuration settings.

    This function sets up the Sentry SDK to monitor the application for errors and performance issues.
    The Sentry events are transformed and sent to Loki using the `sentry_to_loki` function.

    Configuration parameters include:
    - `dsn`: The Data Source Name for the Sentry project.
    - `traces_sample_rate`: The rate at which performance traces are sampled.
    - `environment`: The deployment environment (e.g., production).
    - `release`: The release version of the application.
    - `send_default_pii`: A flag to control the sending of Personally Identifiable Information.
    - `before_send`: A callback function to process events before sending to Sentry.

    Note: If `settings.sentry.dsn` is not provided, a default DSN is used.
    """
    dsn = settings.sentry.dsn
    if not dsn:
        log.error("Sentry DSN not configured, skipping initialization")
        return

    sentry_sdk.init(
        dsn=dsn,  # DSN
        traces_sample_rate=1.0,  # Мониторинг производительности
        environment="production",
        release="1.0.0",
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
        send_default_pii=False  ,  # GDPR
        before_send=sentry_to_loki,  # Вебхук для Loki
    )
