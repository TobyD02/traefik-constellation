from fastapi import FastAPI

app = FastAPI()

@app.get("/new-api")
async def root():
  return {"message": "Hello World"}