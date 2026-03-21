from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import init_db
from app.api.graph import router as graph_router
from app.api.simulation import router as simulation_router
from app.api.report import router as report_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    await init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="MiroFish Mini",
    description="Multi-Agent Simulation Engine",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph_router, prefix="/api/graph")
app.include_router(simulation_router, prefix="/api/simulation")
app.include_router(report_router, prefix="/api/report")


@app.get("/")
async def root():
    return {"status": "ok", "name": "MiroFish Mini"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}
