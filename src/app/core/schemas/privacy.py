"""Схемы для работы с согласием на обработку персональных данных"""

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class PrivacyConsentRequest(BaseModel):
    """Запрос на сохранение согласия на обработку персональных данных"""

    personal_data: Annotated[
        bool,
        Field(
            ..., description="Согласие на обработку персональных данных (обязательно)"
        ),
    ]
    cookies: Annotated[
        bool,
        Field(default=False, description="Согласие на использование файлов cookie"),
    ]
    marketing: Annotated[
        bool, Field(default=False, description="Согласие на маркетинговые коммуникации")
    ]
    timestamp: Annotated[
        Optional[str], Field(None, description="Временная метка согласия в ISO формате")
    ]


class PrivacyConsentResponse(BaseModel):
    """Ответ на сохранение согласия"""

    success: Annotated[bool, Field(..., description="Успешность операции")]
    message: Annotated[str, Field(..., description="Сообщение об результате")]


class ConsentStatusResponse(BaseModel):
    """Ответ со статусом согласия"""

    personal_data: Annotated[
        bool,
        Field(..., description="Наличие согласия на обработку персональных данных"),
    ]
    cookies: Annotated[
        bool, Field(..., description="Наличие согласия на использование cookies")
    ]
    marketing: Annotated[bool, Field(..., description="Наличие согласия на маркетинг")]
    has_consent: Annotated[bool, Field(..., description="Общее наличие согласия")]
    last_updated: Annotated[
        Optional[datetime],
        Field(None, description="Дата последнего обновления согласия"),
    ]


class PrivacyConsentInfo(BaseModel):
    """Информация о согласии"""

    id: Annotated[int, Field(..., description="ID записи согласия")]
    consent_type: Annotated[str, Field(..., description="Тип согласия")]
    is_granted: Annotated[bool, Field(..., description="Статус согласия")]
    granted_at: Annotated[datetime, Field(..., description="Дата согласия")]
    policy_version: Annotated[
        str, Field(..., description="Версия политики конфиденциальности")
    ]
    ip_address: Annotated[str, Field(..., description="IP адрес")]
    user_agent: Annotated[str, Field(..., description="User Agent")]
