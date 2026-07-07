from fastapi import FastAPI

from app.routers import cart, catalog, qr, quotes

app = FastAPI(title="mfg", docs_url=None, redoc_url=None)
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(qr.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
