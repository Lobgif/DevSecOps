from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import ALLOWED_ORIGINS
from routes import position

app = FastAPI(title="FleetTrack")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(position.router)
