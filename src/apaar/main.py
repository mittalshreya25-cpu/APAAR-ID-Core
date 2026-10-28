"""
main.py — FastAPI application factory for APAAR Core.

Wires together middleware, exception handlers, routers, and lifecycle events.
All APAAR identifiers and student data in this system are synthetic / mock.

Security notes
--------------
* Request IDs are generated server-side and not trusted from client headers.
* Tenant context is injected by the auth middleware, never from query params.
* CORS origins must be configured explicitly via ``ALLOWED_ORIGINS`` env var.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apaar.config import get_settings
from apaar.shared.errors import (
    ApaarError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ProcessingError,
    StaleVersionError,
    TenantContextMissing,
    UnauthorizedError,
    ValidationError,
)

# Import all models to ensure full declarative metadata resolution
import apaar.institutions.models  # noqa: F401
import apaar.approvals.models  # noqa: F401
import apaar.identity.models  # noqa: F401
import apaar.submissions.models  # noqa: F401
import apaar.validation.models  # noqa: F401
import apaar.review.models  # noqa: F401
import apaar.attestations.models  # noqa: F401
import apaar.reporting.models  # noqa: F401
import apaar.audit.models  # noqa: F401
import apaar.worker.models  # noqa: F401

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Runs startup logic before yield, teardown after.
    """
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info(
        "APAAR Core starting",
        extra={"version": app.version, "debug": settings.DEBUG},
    )

    yield

    # Teardown
    try:
        from apaar.database import get_engine

        await get_engine().dispose()
        logger.info("Database engine disposed.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error disposing database engine: %s", exc)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="APAAR Core API",
        version="0.1.0",
        summary="Institutional enrolment assurance platform for AICTE PS-26263.",
        description=(
            "**All student identifiers and APAAR tokens in this system are "
            "synthetic/mock.** No real Aadhaar numbers or government credentials "
            "are collected or stored. This is a prototype for demonstration purposes."
        ),
        openapi_url="/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ----- Middleware -------------------------------------------------------

    # CORS — must be first in the middleware stack
    allowed_origins: list[str] = settings.ALLOWED_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # Request-ID + structured-log middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        """Inject a server-generated request ID and log request/response."""
        # Generate ID server-side; never trust the client's value blindly.
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
            },
        )
        return response

    # ----- Exception handlers -----------------------------------------------

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=exc.to_dict())

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content=exc.to_dict())

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(
        request: Request, exc: UnauthorizedError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content=exc.to_dict())

    @app.exception_handler(StaleVersionError)
    async def stale_version_handler(
        request: Request, exc: StaleVersionError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content=exc.to_dict())

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content=exc.to_dict())

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content=exc.to_dict())

    @app.exception_handler(ProcessingError)
    async def processing_error_handler(
        request: Request, exc: ProcessingError
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content=exc.to_dict())

    @app.exception_handler(TenantContextMissing)
    async def tenant_ctx_handler(
        request: Request, exc: TenantContextMissing
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content=exc.to_dict())

    @app.exception_handler(ApaarError)
    async def apaar_error_handler(request: Request, exc: ApaarError) -> JSONResponse:
        # Catch-all for any other domain errors not explicitly handled above.
        logger.exception("Unhandled domain error: %s", exc)
        return JSONResponse(status_code=500, content=exc.to_dict())

    # ----- Routers ----------------------------------------------------------
    # Routers are registered conditionally as modules are built out.
    # Each module exposes an `api_router` once its router file exists.

    _register_routers(app)

    # ----- System endpoints -------------------------------------------------

    from pathlib import Path

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", tags=["system"], include_in_schema=False)
        async def root() -> FileResponse:
            """Serve interactive demonstration UI."""
            return FileResponse(str(static_dir / "index.html"))

    @app.get("/health", tags=["system"], summary="Liveness check")
    async def health() -> dict:
        """Return 200 OK if the application process is running."""
        return {"status": "ok", "synthetic_mode": True}

    @app.get("/ready", tags=["system"], summary="Readiness check")
    async def ready() -> dict:
        """Return 200 OK if the application is ready to serve traffic.

        Checks database connectivity. Returns 503 if the DB is unreachable.
        """
        from fastapi import HTTPException

        try:
            import sqlalchemy

            from apaar.database import get_session_factory

            async with get_session_factory()() as session:
                await session.execute(sqlalchemy.text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001
            logger.error("Readiness check failed: %s", exc)
            raise HTTPException(status_code=503, detail="Database unavailable") from exc

        return {"status": "ready", "synthetic_mode": True}

    return app


def _register_routers(app: FastAPI) -> None:
    """Attempt to import and register each module's router.

    Routers that do not yet exist are silently skipped so the app remains
    runnable during incremental development.
    """
    _module_routers = [
        ("apaar.institutions.router", "/api/v1/institutions", ["institutions"]),
        ("apaar.access.router", "/api/v1/access", ["access"]),
        ("apaar.approvals.router", "/api/v1/approvals", ["approvals"]),
        ("apaar.identity.router", "/api/v1/identity", ["identity"]),
        ("apaar.submissions.router", "/api/v1/submissions", ["submissions"]),
        ("apaar.validation.router", "/api/v1/validation", ["validation"]),
        ("apaar.review.router", "/api/v1/review", ["review"]),
        ("apaar.attestations.router", "/api/v1/attestations", ["attestations"]),
        ("apaar.reporting.router", "/api/v1/reporting", ["reporting"]),
        ("apaar.audit.router", "/api/v1/audit", ["audit"]),
        ("apaar.worker.router", "/api/v1/worker", ["worker"]),
    ]

    for module_path, prefix, tags in _module_routers:
        try:
            import importlib

            mod = importlib.import_module(module_path)
            router = getattr(mod, "api_router", None)
            if router is not None:
                app.include_router(router, prefix=prefix, tags=tags)
                logger.debug("Registered router: %s at %s", module_path, prefix)
            else:
                logger.debug("Module %s has no api_router; skipping.", module_path)
        except ModuleNotFoundError:
            logger.debug("Router module %s not yet implemented; skipping.", module_path)
        except Exception as exc:  # noqa: BLE001
            # Any other import error is logged as a warning so the app still starts.
            logger.warning(
                "Failed to import router from %s: %s", module_path, exc, exc_info=True
            )


# ---------------------------------------------------------------------------
# Application singleton
# ---------------------------------------------------------------------------

app = create_app()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Run the application with Uvicorn (used in development)."""
    settings = get_settings()
    uvicorn.run(
        "apaar.main:app",
        host="0.0.0.0",  # noqa: S104 — binding to all interfaces is expected for container
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    run()
