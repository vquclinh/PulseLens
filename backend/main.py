# FastAPI application entry point — registers all API routers and configures CORS
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import report, chat, stock

app = FastAPI(title="PulseLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report.router)
app.include_router(chat.router)
app.include_router(stock.router)
