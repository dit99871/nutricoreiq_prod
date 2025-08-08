from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from src.app.core.services.auth import get_current_auth_user
from src.app.core.utils import templates
from src.app.schemas.user import UserResponse

router = APIRouter(
    tags=["Info"],
    default_response_class=HTMLResponse,
)


@router.get("/privacy")
def get_privacy_info(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    """
    Retrieves the privacy policy information of the NutriCoreIQ project.

    This endpoint renders an HTML template with the privacy policy details,
    including information on data collection, usage, and protection.

    :param request: The incoming request object.
    :param current_user: The authenticated user object obtained from the dependency.
    :return: A rendered HTML template with the privacy policy information.
    """

    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={
            "user": current_user,
            "current_year": datetime.now().year,
            "csp_nonce": request.state.csp_nonce,
        },
    )


@router.get("/about")
def get_info_about_project(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    """
    Retrieves information about the NutriCoreIQ project.

    This endpoint renders an HTML template with information about the project,
    including its goals, features, and team.

    :param request: The incoming request object.
    :param current_user: The authenticated user object obtained from the dependency.
    :return: A rendered HTML template with information about the project.
    """

    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={
            "user": current_user,
            "current_year": datetime.now().year,
            "csp_nonce": request.state.csp_nonce,
        },
    )
