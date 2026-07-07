from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import close_pool
from app.routers import catalog, qr


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_pool()


app = FastAPI(title="mfg", docs_url=None, redoc_url=None, lifespan=lifespan)
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(qr.router, prefix="/api/v1")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
