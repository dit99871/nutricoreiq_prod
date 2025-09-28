from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from src.app.core import templates
from src.app.core.services.user_service import UserService
from src.app.schemas.user import UserPublic

router = APIRouter(
    tags=["Info"],
    default_response_class=HTMLResponse,
)

current_user = Annotated[UserPublic, Depends(UserService.get_current_auth_user)]


@router.get("/privacy")
def get_privacy_info(
    request: Request,
    user: current_user,
):
    """
    Retrieves the privacy policy information of the NutriCoreIQ project.

    This endpoint renders an HTML template with the privacy policy details,
    including information on data collection, usage, and protection.

    :param request: The incoming request object.
    :param user: The authenticated user object obtained from the dependency.
    :return: A rendered HTML template with the privacy policy information.
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
    user: current_user,
):
    """
    Retrieves information about the NutriCoreIQ project.

    This endpoint renders an HTML template with information about the project,
    including its goals, features, and team.

    :param request: The incoming request object.
    :param user: The authenticated user object obtained from the dependency.
    :return: A rendered HTML template with information about the project.
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
    user: current_user,
):
    """
    Retrieves the home page of NutriCoreIQ.

    This endpoint renders an HTML template for the home page, which
    displays a welcome message and the current year.

    :param request: The incoming request object.
    :param user: The authenticated user object obtained from the dependency.
    :return: A rendered HTML template for the home page.
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
