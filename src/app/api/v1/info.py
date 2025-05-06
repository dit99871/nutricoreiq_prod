from fastapi import APIRouter, Request

from utils.security import generate_csp_nonce
from utils.templates import templates

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
            "csp_nonce": generate_csp_nonce(),
        },
    )


@router.get("/about")
def get_info_about_project(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        content={
            "csp_nonce": generate_csp_nonce(),
        },
    )
