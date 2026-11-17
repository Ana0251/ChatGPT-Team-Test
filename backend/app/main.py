"""FastAPI application factory and minimal health endpoint (H-03 only)."""

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.modules.identity.router import router as identity_router
from app.modules.companies.router import router as companies_router
from app.modules.fiscal.router import router as fiscal_router
from app.modules.accounts.router import router as accounts_router
from app.modules.audit.router import router as audit_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application without database, migration, or auth side effects."""
    config = settings if settings is not None else get_settings()
    application = FastAPI(title=config.app_name, version="0.1.0")
    application.include_router(identity_router, prefix="/api/v1")
    application.include_router(companies_router, prefix="/api/v1")
    application.include_router(fiscal_router, prefix="/api/v1")
    application.include_router(accounts_router, prefix="/api/v1")
    application.include_router(audit_router, prefix="/api/v1")

    @application.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        """Report that the HTTP application is reachable."""
        return {"status": "ok"}

    return application


app = create_app()
