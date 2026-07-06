from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import transcribe, transcripts

app = FastAPI(title="YouTube Transcript API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # Must be False when allow_origins is "*" (browsers reject "*" + credentials).
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcribe.router)
app.include_router(transcripts.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
