"""FastAPI application for Task 3.

Run from the repository root:
    uvicorn api.main:app --reload
Interactive docs are served at http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.database import close_connections
from api.routers import mongo_prices, sql_prices


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_connections()


app = FastAPI(
    title="AAPL Stock Time-Series API",
    description=(
        "CRUD and time-series queries over the Task 2 databases. "
        "Every endpoint exists under /sql (MySQL) and /mongo (MongoDB)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(sql_prices.router)
app.include_router(mongo_prices.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "docs": "/docs"}
