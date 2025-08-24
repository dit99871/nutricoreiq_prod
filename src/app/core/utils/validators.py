from __future__ import annotations

from typing import Any

from src.app.models.user import KFALevel, GoalType


def validate_password_strength(v: str) -> str:
    """
    Проверяет сложность пароля: наличие строчных и прописных букв, цифр и спецсимволов.
    Возвращает пароль без изменений, если проверка пройдена, иначе поднимает ValueError.
    """
    has_lower = any(c.islower() for c in v)
    has_upper = any(c.isupper() for c in v)
    has_digit = any(c.isdigit() for c in v)
    has_special = any(not c.isalnum() for c in v)
    if not (has_lower and has_upper and has_digit and has_special):
        raise ValueError(
            "Пароль должен содержать строчные и прописные буквы, цифры и спецсимволы"
        )
    return v


def coerce_kfa(v: Any) -> KFALevel | None:
    """
    Преобразует вход в KFALevel или None.
    Допускает значения: None, "", экземпляр KFALevel, строковое/числовое значение Enum.
    """
    if v in (None, ""):
        return None
    if isinstance(v, KFALevel):
        return v
    s = str(v)
    for m in KFALevel:
        if m.value == s:
            return m
    raise ValueError(f"Недопустимое значение kfa: {v}")


def coerce_goal(v: Any) -> GoalType | None:
    """
    Преобразует вход в GoalType или None.
    Допускает значения: None, "", экземпляр GoalType, строковое значение Enum.
    """
    if v in (None, ""):
        return None
    if isinstance(v, GoalType):
        return v
    try:
        return GoalType(v)
    except Exception:
        raise ValueError(f"Недопустимое значение goal: {v}")
