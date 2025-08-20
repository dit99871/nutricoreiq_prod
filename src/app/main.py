from fastapi import FastAPI

from src.app.core.app import create_app
from src.app.core.logger import setup_logging

setup_logging()

app: FastAPI = create_app()
