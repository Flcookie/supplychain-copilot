from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import chat, workbench
from core.config import log_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_config()
    yield


app = FastAPI(
    title="Supplier Lifecycle Copilot API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(workbench.router)

try:
    from api.routes import skillhub as skillhub_routes
except ImportError:
    skillhub_routes = None
else:
    app.include_router(skillhub_routes.router)
    _skillhub_web = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "skillhub", "web"
    )
    if os.path.isdir(_skillhub_web):
        app.mount(
            "/skillhub",
            StaticFiles(directory=_skillhub_web, html=True),
            name="skillhub-web",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


_frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "dist"
)
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
