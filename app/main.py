from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api.research import router as research_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)


@app.get("/")
async def root():
    return {
        "message": "Research Engine API running"
    }