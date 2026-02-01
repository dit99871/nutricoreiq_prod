from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.responses import HTMLResponse, ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from src.app.core import db_helper
from src.app.core.exceptions import ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.core.services.user_service import UserService, get_user_service
from src.app.core.utils import templates
from src.app.core.repo.profile import get_user_profile, update_user_profile
from src.app.core.repo.user import choose_subscribe_status
from src.app.core.models.user import KFALevel
from src.app.core.schemas.user import UserProfileUpdate, UserPublic

router = APIRouter(
    tags=["User"],
    default_response_class=ORJSONResponse,
)

log = get_logger("user_router")

# алиасы типов зависимостей
session_dep = Annotated[AsyncSession, Depends(db_helper.session_getter)]
current_user_dep = Annotated[UserPublic, Depends(UserService.get_user_by_access_jwt)]
user_service_dep = Annotated[UserService, Depends(get_user_service)]


@router.get("/me")
async def read_current_user(
    user: current_user_dep,
) -> dict:
    """
    Retrieves the current authenticated user's basic information.

    This endpoint returns the username and email of the authenticated user.
    If the user is not authenticated, it raises an HTTPException with a 401 status code.

    :param user: The authenticated user object obtained from the dependency.
    :return: A dictionary containing the username and email of the user.
    :raises HTTPException: If the user is not authenticated.
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
    db_session: session_dep,
    user_service: user_service_dep,
) -> Response:
    """
    Retrieves the current authenticated user's profile information.

    This endpoint returns the profile information of the authenticated user.
    If the user is not authenticated, it raises an HTTPException with a 401 status code.

    :param request: The incoming request object.
    :param user: The authenticated user object obtained from the dependency.
    :param db_session: The current database db_session.
    :param user_service: The user service instance.
    :return: A rendered HTML template with the user's profile information.
    :raises HTTPException: If the user is not authenticated.
    """

    if user is None:
        log.warning("Пользователь не авторизован")
        raise ExpiredTokenException()

    user = await get_user_profile(db_session, user.id)

    # Расчет нутриентов через сервисный слой
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
    db_session: session_dep,
) -> dict:
    """
    Updates the current authenticated user's profile information.

    This endpoint accepts a `UserProfile` object containing the updated
    profile details and updates the current user's profile in the database.
    If the user is not authenticated, it raises a 401 HTTPException. If
    the provided data is invalid, it raises a 400 HTTPException.

    :param data_in: The updated user profile information.
    :param user: The authenticated user object obtained from the dependency.
    :param db_session: The current database db_session.
    :return: A JSON response indicating the success of the profile update.
    :raises HTTPException: If the user is not authenticated or if the provided data is invalid.
    """

    if user is None:
        raise ExpiredTokenException()

    if not data_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Произошла ошибка. Попробуйте позже!",
            },
        )
    await update_user_profile(data_in, user, db_session)

    return {"message": "Profile updated successfully"}


@router.post("/unsubscribe")
async def unsubscribe_email_notification(
    user: current_user_dep,
    db_session: session_dep,
) -> None:
    """
    Unsubscribes the current authenticated user from email notifications.

    This endpoint accepts the current authenticated user object and the
    current database session. It then calls the `choose_subscribe_status`
    function with the user object and the database session, along with the
    boolean value `False` to indicate that the user wants to unsubscribe from
    email notifications. If the user is not authenticated, it raises an
    HTTPException with a 401 status code.

    :param user: The authenticated user object obtained from the dependency.
    :param db_session: The current database db_session.
    :return: A JSON response indicating the success of the unsubscription.
    :raises HTTPException: If the user is not authenticated.
    """

    if user is None:
        raise ExpiredTokenException()

    await choose_subscribe_status(user, db_session, False)


@router.post("/subscribe")
async def subscribe_email_notification(
    user: current_user_dep,
    db_session: session_dep,
) -> None:
    """
    Subscribes the current authenticated user to email notifications.

    This endpoint accepts the current authenticated user object and the
    current database session. It then calls the `choose_subscribe_status`
    function with the user object and the database session, along with the
    boolean value `True` to indicate that the user wants to subscribe to
    email notifications. If the user is not authenticated, it raises an
    HTTPException with a 401 status code.

    :param user: The authenticated user object obtained from the dependency.
    :param db_session: The current database db_session.
    :return: A JSON response indicating the success of the subscription.
    :raises HTTPException: If the user is not authenticated.
    """

    if user is None:
        raise ExpiredTokenException()

    await choose_subscribe_status(user, db_session, True)


@router.get("/login")
async def login_get() -> RedirectResponse:
    """
    Redirects the user to the homepage with an action parameter set to unsubscribe.

    This endpoint is used to handle login requests to the `/login` endpoint.
    It returns a 302 redirect response to the homepage with an action parameter set to unsubscribe.

    :return: A 302 redirect response.
    """

    return RedirectResponse(url="/?action=unsubscribe")
