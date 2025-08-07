from datetime import datetime

from fastapi import APIRouter, Request

from src.app.utils.templates import templates

router = APIRouter(tags=["Info"])


@router.get("/privacy")
def get_privacy_info(request: Request):
    """
    Returns the privacy policy page.

    This page is a static HTML template that displays the privacy policy.

    :param request: The incoming request object.
    :return: A rendered HTML template with the privacy policy.
    """

    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        content={
            "current_year": datetime.now().year,
            "csp_nonce": request.state.csp_nonce,
        },
    )


@router.get("/about")
def get_info_about_project(request: Request):
    """
    Returns the about page.

    This page is a static HTML template that displays the description of the project.

    :param request: The incoming request object.
    :return: A rendered HTML template with the about page.
    """

    return templates.TemplateResponse(
        request=request,
        name="about.html",
        content={
            "current_year": datetime.now().year,
            "csp_nonce": request.state.csp_nonce,
        },
    )
