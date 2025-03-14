import uvicorn
from fastapi import FastAPI

from core.config import settings
from utils.logger import setup_logging

setup_logging()

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
