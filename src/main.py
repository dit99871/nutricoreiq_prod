from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def main():
    return {"message": "Hi, searching!"}


if __name__ == "__main__":
    main()
    о