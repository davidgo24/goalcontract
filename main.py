from fastapi import FastAPI

app = FastAPI()

@app.get("/")

@app.get("/")
async def read_root():
    return {"message": "Sistema API Testing :)"}

