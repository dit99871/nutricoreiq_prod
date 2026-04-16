"""`Info` эндпоинты."""

from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from src.app.core import templates
from src.app.core.dependencies import current_user_dep

router = APIRouter(
    tags=["Info"],
    default_response_class=HTMLResponse,
)


@router.get("/privacy")
def get_privacy_info(
    request: Request,
    user: current_user_dep,
):
    """
    Получает информацию о политике конфиденциальности проекта NutriCoreIQ.

    Этот эндпоинт рендерит HTML-шаблон с деталями политики конфиденциальности,
    включая информацию о сборе, использовании и защите данных.

    :param request: Входящий объект запроса.
    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :return: Отрендеренный HTML-шаблон с информацией о политике конфиденциальности.
    """

    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={
            "user": user,
            "current_year": datetime.now().year,
            "csp_nonce": request.state.csp_nonce,
        },
    )


@router.get("/about")
def get_info_about_project(
    request: Request,
    user: current_user_dep,
):
    """
    Получает информацию о проекте NutriCoreIQ.

    Этот эндпоинт рендерит HTML-шаблон с информацией о проекте,
    включая его цели, функции и команду.

    :param request: Входящий объект запроса.
    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :return: Отрендеренный HTML-шаблон с информацией о проекте.
    """

    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={
            "user": user,
            "current_year": datetime.now().year,
            "csp_nonce": request.state.csp_nonce,
        },
    )


@router.get(
    "/",
    name="home",
)
def start_page(
    request: Request,
    user: current_user_dep,
):
    """
    Получает домашнюю страницу NutriCoreIQ.

    Этот эндпоинт рендерит HTML-шаблон для домашней страницы, который
    отображает приветственное сообщение и текущий год.

    :param request: Входящий объект запроса.
    :param user: Аутентифицированный объект пользователя, полученный из зависимости.
    :return: Отрендеренный HTML-шаблон для домашней страницы.
    """

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_year": datetime.now().year,
            "user": user,
            "csp_nonce": request.state.csp_nonce,
        },
    )


@router.head("/")
def start_page_head() -> Response:
    """HEAD для аптайм-мониторинга (Sentry и др.) — возвращает только заголовки."""

    return Response()
