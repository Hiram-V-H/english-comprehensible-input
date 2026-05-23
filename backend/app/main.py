from __future__ import annotations

import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .api.router import api_router
from .config import settings
from .exceptions import AppException
from .middleware import app_exception_handler


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control: no-cache to JS/CSS files so the browser always fetches fresh versions."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.endswith(('.js', '.css', '.html')):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure data directory and database exist
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.materials_raw_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.materials_processed_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.materials_failed_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Comprehensible Input English Learning System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)

# No-cache middleware MUST be added before StaticFiles mount to take effect
app.add_middleware(NoCacheStaticMiddleware)

app.include_router(api_router, prefix="/api")

# Mount frontend static files
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
