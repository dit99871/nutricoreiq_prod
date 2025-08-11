from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse

from src.app.core.app import create_app
from src.app.core.config import settings
from src.app.core.logger import setup_logging
from src.app.core.utils import templates
from src.app.schemas.user import UserResponse
from src.app.core.services.auth import get_current_auth_user

setup_logging()

app: FastAPI = create_app()


@app.get(
    "/",
    name="home",
    response_class=HTMLResponse,
)
def start_page(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_year": datetime.now().year,
            "user": current_user,
            "csp_nonce": request.state.csp_nonce,
        },
    )

