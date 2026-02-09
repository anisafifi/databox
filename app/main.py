from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.graphql import graphql_router
from .api.rest import public_router, router as rest_router
from .core.config import settings
from .core.limits import InMemoryRateLimiter, RateLimitConfig, RequestIdAndRateLimitMiddleware
from .core.logging_config import RequestLoggingMiddleware, setup_logging

setup_logging(settings.log_level)

openapi_servers = [{"url": settings.server_url}] if settings.server_url else None

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=openapi_servers,
)


@app.middleware("http")
async def strip_server_header(request, call_next):
    response = await call_next(request)
    if "server" in response.headers:
        del response.headers["server"]
    return response

app.add_middleware(
    RequestIdAndRateLimitMiddleware,
    limiter=InMemoryRateLimiter(RateLimitConfig(limit=settings.rate_limit_per_minute)),
)
app.add_middleware(RequestLoggingMiddleware)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(public_router, prefix="/v1")
app.include_router(rest_router, prefix="/v1")
app.include_router(graphql_router, prefix="/v1/graphql")
