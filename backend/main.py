# FastAPI application entry point — registers all API routers and configures CORS
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import report, chat, stock

app = FastAPI(title="PulseLens API")

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report.router)
app.include_router(chat.router)
app.include_router(stock.router)
