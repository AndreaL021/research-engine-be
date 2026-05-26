from fastapi import FastAPI

from app.api.research import router as research_router

app = FastAPI()


app.include_router(research_router)


@app.get("/")
async def root():
    return {
        "message": "Research Engine API running"
    }