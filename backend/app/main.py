from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes_auth import router as auth_router
from app.db.session import engine
from app.db.models import Base

app = FastAPI(title=settings.APP_NAME)

# If your UI runs on a different port/domain, enable CORS.
# You can tighten this later (e.g., only your UI origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def on_shutdown():
    # Place graceful cleanup here if you add global resources later.
    # (Right now, nothing global to close.)
    pass
