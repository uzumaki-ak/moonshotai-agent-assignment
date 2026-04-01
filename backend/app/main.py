# this file bootstraps fastapi app and router setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # this hook ensures tables exist for local development
    Base.metadata.create_all(bind=engine)


app.include_router(api_router, prefix=settings.api_v1_prefix)
