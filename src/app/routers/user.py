"""Эндпоинты для работы с пользователями."""

from datetime import datetime

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import RedirectResponse

from src.app.core.dependencies import (
    current_user_dep,
    db_session_dep,
    user_service_dep,
)
from src.app.core.exceptions import ExpiredTokenException, ValidationError
from src.app.core.logger import get_logger
from src.app.core.models.user import KFALevel
from src.app.core.repo.profile import get_user_profile, update_user_profile
from src.app.core.repo.user import choose_subscribe_status
from src.app.core.schemas.user import UserProfileUpdate
from src.app.core.utils import templates

router = APIRouter(
    tags=["User"],
    default_response_class=JSONResponse,
)

log = get_logger("user_router")


@router.get("/me")
async def read_current_user(
    user: current_user_dep,
) -> dict:
    """
    Получает базовую информацию о текущем аутентифицированном пользователе.

    Этот эндпоинт возвращает имя пользователя и email аутентифицированного пользователя.
    Если пользователь не аутентифицирован, вызывает ExpiredTokenException с кодом 401.

    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :return: Словарь, содержащий имя пользователя и email.
    :raises ExpiredTokenException: Если пользователь не аутентифицирован.
    """

    if user is None:
        raise ExpiredTokenException()

    return {
        "username": user.username,
        "email": user.email,
    }


@router.get("/profile/data", response_class=HTMLResponse)
@router.head("/profile/data")
async def get_profile(
    request: Request,
    user: current_user_dep,
    db_session: db_session_dep,
    user_service: user_service_dep,
) -> Response:
    """
    Получает информацию о профиле текущего аутентифицированного пользователя.

    Этот эндпоинт возвращает информацию о профиле аутентифицированного пользователя.
    Если пользователь не аутентифицирован, вызывает ExpiredTokenException с кодом 401.

    :param request: Входящий объект запроса.
    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :param db_session: Текущая сессия базы данных.
    :param user_service: Экземпляр сервиса пользователя.
    :return: Отрендеренный HTML-шаблон с информацией о профиле пользователя.
    :raises ExpiredTokenException: Если пользователь не аутентифицирован.
    """

    if user is None:
        log.warning("Пользователь не авторизован")
        raise ExpiredTokenException()

    user = await get_user_profile(db_session, user.id)

    # расчет нутриентов через сервисный слой
    nutrition_data = user_service.calculate_user_nutrients(user)
    is_filled = nutrition_data is not None

    tdee = nutrition_data["tdee"] if nutrition_data else None
    nutrients = nutrition_data["nutrients"] if nutrition_data else None

    return templates.TemplateResponse(
        name="profile.html",
        request=request,
        context={
            "current_year": datetime.now().year,
            "csp_nonce": request.state.csp_nonce,
            "user": user,
            "is_subscribed": user.is_subscribed,
            "is_filled": is_filled,
            "tdee": tdee,
            "nutrients": nutrients,
            "KFALevel": KFALevel,
        },
    )


@router.post("/profile/update")
async def update_profile(
    data_in: UserProfileUpdate,
    user: current_user_dep,
    db_session: db_session_dep,
) -> dict:
    """
    Обновляет информацию о профиле текущего аутентифицированного пользователя.

    Этот эндпоинт принимает объект `UserProfile`, содержащий обновленные
    детали профиля и обновляет профиль текущего пользователя в базе данных.
    Если пользователь не аутентифицирован, вызывает ExpiredTokenException с кодом 401. Если
    предоставленные данные невалидны, вызывает ValidationError с кодом 400.

    :param data_in: Обновленная информация о профиле пользователя.
    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :param db_session: Текущая сессия базы данных.
    :return: JSON-ответ, указывающий на успешное обновление профиля.
    :raises ExpiredTokenException: Если пользователь не аутентифицирован или.
    :raises ValidationError: Если предоставленные данные невалидны.
    """

    if user is None:
        raise ExpiredTokenException()

    if not data_in:
        raise ValidationError("Произошла ошибка. Попробуйте позже!")
    await update_user_profile(data_in, user, db_session)

    return {"message": "Profile updated successfully"}


@router.post("/unsubscribe")
async def unsubscribe_email_notification(
    user: current_user_dep,
    db_session: db_session_dep,
) -> None:
    """
    Отписывает текущего аутентифицированного пользователя от email-уведомлений.

    Этот эндпоинт принимает объект текущего аутентифицированного пользователя и
    текущую сессию базы данных. Затем вызывает функцию `choose_subscribe_status`
    с объектом пользователя и сессией базы данных, а также с булевым значением `False`,
    указывающим, что пользователь хочет отписаться от email-уведомлений.

    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :param db_session: Текущая сессия базы данных.
    :return: JSON-ответ, указывающий на успешную отписку.
    :raises ExpiredTokenExceptio: Если пользователь не аутентифицирован.
    """

    if user is None:
        raise ExpiredTokenException()

    await choose_subscribe_status(user, db_session, False)


@router.post("/subscribe")
async def subscribe_email_notification(
    user: current_user_dep,
    db_session: db_session_dep,
) -> None:
    """
    Подписывает текущего аутентифицированного пользователя на email-уведомления.

    Этот эндпоинт принимает объект текущего аутентифицированного пользователя и
    текущую сессию базы данных. Затем вызывает функцию `choose_subscribe_status`
    с объектом пользователя и сессией базы данных, а также с булевым значением `True`,
    указывающим, что пользователь хочет подписаться на email-уведомления. Если пользователь
    не аутентифицирован, вызывает HTTPException с кодом 401.

    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :param db_session: Текущая сессия базы данных.
    :return: JSON-ответ, указывающий на успешную подписку.
    :raises ExpiredTokenException: Если пользователь не аутентифицирован.
    """

    if user is None:
        raise ExpiredTokenException()

    await choose_subscribe_status(user, db_session, True)


@router.get("/login")
async def login_get() -> RedirectResponse:
    """
    Перенаправляет пользователя на домашнюю страницу с параметром действия, установленным в unsubscribe.

    Этот эндпоинт используется для обработки запросов на вход к эндпоинту `/login`.
    Возвращает ответ с редиректом 302 на домашнюю страницу с параметром действия, установленным в unsubscribe.

    :return: Ответ с редиректом 302.
    """

    return RedirectResponse(url="/?action=unsubscribe")
