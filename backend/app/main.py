from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes_auth import router as auth_router
from app.db.session import engine
from app.db.models import Base
from fastapi import APIRouter
from app.api.routes_enrollment import router as enroll_router
from app.api.routes_identify import router as identify_router


app = FastAPI(title=settings.APP_NAME)

#routers
app.include_router(auth_router)
app.include_router(enroll_router)
app.include_router(identify_router)


# If your UI runs on a different port/domain, enable CORS.
# You can tighten this later (e.g., only your UI origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
