import json
import time
from datetime import datetime

import httpx

from src.app.core import broker
from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("sentry_task")


@broker.task(
    max_retries=3,
    retry_delay=30,
)
async def send_event_to_loki(
    event_id: str | None,
    message: str,
    level: str,
) -> None:
    loki_url = settings.loki.url
    log_entry = {
        "streams": [
            {
                "stream": {
                    "source": "sentry",
                    "level": level,
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
                                "message": message,
                                "event_id": event_id,
                            }
                        ),
                    ]
                ],
            }
        ]
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(loki_url, json=log_entry)
            response.raise_for_status()
        log.info("Успешно отправлено в Loki: %s", event_id)
    except Exception as e:
        log.error("Ошибка при отправлении в Loki: %s, error: %s", loki_url, e)
        raise  # raise нужен, чтобы taskiq мог сделать retry
