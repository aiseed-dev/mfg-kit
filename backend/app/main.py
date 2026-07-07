from fastapi import FastAPI

from app.routers import catalog, qr

app = FastAPI(title="mfg", docs_url=None, redoc_url=None)
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(qr.router, prefix="/api/v1")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
