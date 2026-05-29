# FastAPI application entry point — registers all API routers and configures CORS.
#
# CRITICAL: load_dotenv() must be the FIRST call in this file, before any
# `from app.*` imports.  `app/db/__init__.py` creates the db_adapter singleton
# at import time by reading DATABASE_BACKEND.  If dotenv is loaded after those
# imports, the adapter is already built with the wrong (default sqlite) backend.
from dotenv import load_dotenv
load_dotenv()   # loads backend/.env — no-op if vars are already set in the shell

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import report, chat, stock

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Emit a clear startup line so operators can confirm which DB backend is live.
_db_backend = os.getenv("DATABASE_BACKEND", "sqlite").lower()
_db_url_present = bool(os.getenv("DATABASE_URL"))
logger.info("Database backend selected: %s", _db_backend)
logger.info("DATABASE_URL present: %s", str(_db_url_present).lower())
if _db_backend == "postgres" and not _db_url_present:
    logger.warning("DATABASE_BACKEND=postgres but DATABASE_URL is not set — startup will fail")

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
