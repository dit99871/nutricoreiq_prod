import uvicorn
from fastapi import FastAPI

from api.v1 import user_router
from core.config import settings
from utils.logger import setup_logging

setup_logging()

app = FastAPI()
app.include_router(user_router)


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
