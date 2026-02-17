from __future__ import annotations

import argparse
import asyncio
import time

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.agents.events import worker_loop
from app.api import api_router
from app.clickhouse.client import init_clickhouse
from app.config import get_settings
from app.db.postgres import close_postgres, init_postgres
from app.logging import configure_logging
from app.metrics import http_request_duration_seconds
from app.storage.minio_client import init_minio
from app.tracing import init_tracing
from app.websocket import router as events_router

settings = get_settings()

app = FastAPI(
    title="SonataOps Studio API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup_event() -> None:
    configure_logging(settings.log_level)
    init_tracing(app, settings.app_name, settings.otel_exporter_otlp_endpoint)
    await init_postgres()
    init_clickhouse()
    init_minio()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_postgres()


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    status = 500
    route = request.url.path
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        http_request_duration_seconds.labels(
            method=request.method,
            route=route,
            status=str(status),
        ).observe(elapsed)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(api_router)
app.include_router(events_router)


async def run_worker() -> None:
    configure_logging(settings.log_level)
    worker_app = FastAPI()
    init_tracing(worker_app, f"{settings.app_name}-worker", settings.otel_exporter_otlp_endpoint)
    await init_postgres()
    init_clickhouse()
    init_minio()
    await worker_loop()


def main() -> None:
    parser = argparse.ArgumentParser(description="SonataOps Studio backend entrypoint")
    parser.add_argument("mode", nargs="?", default="api", choices=["api", "worker"])
    args = parser.parse_args()

    if args.mode == "worker":
        asyncio.run(run_worker())
        return

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
