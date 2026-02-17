from fastapi import APIRouter

from app.api import (
    routes_admin,
    routes_anomalies,
    routes_audio,
    routes_briefs,
    routes_health,
    routes_kpis,
    routes_rag,
)

api_router = APIRouter()
api_router.include_router(routes_health.router)
api_router.include_router(routes_kpis.router)
api_router.include_router(routes_anomalies.router)
api_router.include_router(routes_audio.router)
api_router.include_router(routes_rag.router)
api_router.include_router(routes_briefs.router)
api_router.include_router(routes_admin.router)
