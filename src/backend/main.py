import uvicorn
from fastapi import FastAPI

from core.config import settings

app = FastAPI()


@app.get("/")
def main():
    return {"message": "Hi, searching!"}


if __name__ == "__main__":
    uvicorn.run(app, host=settings.run.host, port=settings.run.port)
