import logging

import uvicorn
from fastapi import FastAPI

from core.config import settings

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)

app = FastAPI()


@app.get("/")
def main():
    return {"message": "Hi, searching!"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
