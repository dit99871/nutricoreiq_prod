from fastapi import FastAPI

from src.app.core.app import create_app
from src.app.core.logger import setup_logging

setup_logging()

app: FastAPI = create_app()


if __name__ == "__main__":
    from src.app.core.config import settings

    if settings.env.env == "dev":
        import subprocess

        import uvicorn

        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.dev.yml",
                "up",
                "-d",
                "--remove-orphans",
            ],
            check=True,
        )
        uvicorn.run(
            "src.app.main:app",
            host=settings.run.host,
            port=settings.run.port,
            reload=True,
        )
