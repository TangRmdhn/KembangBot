# API package for Kembang AI

from app.api.webhook import router as webhook_router
from app.api.tenants import router as tenants_router
from app.api.conversations import router as conversations_router
from app.api.stages import router as stages_router
from app.api.leads import router as leads_router
from app.api.catalog import router as catalog_router
from app.api.health import router as health_router
from app.api.internal import router as internal_router
from app.api.documents import router as documents_router

all_routers = [
    webhook_router,
    tenants_router,
    conversations_router,
    stages_router,
    leads_router,
    catalog_router,
    health_router,
    internal_router,
    documents_router,
]
