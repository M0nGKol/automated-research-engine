"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import router
from app.api.routes import limiter
from app.config import get_settings
from app.db import init_db


class CORSErrorMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure CORS headers are added to all responses, including errors."""
    
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        origin = request.headers.get("origin", "")
        allowed_origins = settings.cors_origins_list
        
        # Determine allowed origin
        if origin in allowed_origins:
            allowed_origin = origin
        elif "*" in allowed_origins:
            allowed_origin = "*"
        else:
            allowed_origin = None
        
        try:
            response = await call_next(request)
            # Add CORS headers to successful responses
            if allowed_origin:
                response.headers["Access-Control-Allow-Origin"] = allowed_origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        except Exception as exc:
            # Add CORS headers to error responses
            if allowed_origin:
                return JSONResponse(
                    status_code=500,
                    content={"detail": str(exc)},
                    headers={
                        "Access-Control-Allow-Origin": allowed_origin,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                    },
                )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"🚀 Research Agent API starting...")
    print(f"   Provider: {settings.llm_provider}")
    print(f"   Model: {settings.llm_model}")
    if settings.llm_provider == "ollama":
        print(f"   Ollama URL: {settings.ollama_base_url}")
    else:
        print(f"   vLLM URL: {settings.vllm_base_url}")
    print(f"   Max sources: {settings.max_sources_to_process}")
    print(f"   CORS origins: {settings.cors_origins_list}")  # Debug: print CORS config
    
    # Initialize database
    print("   Initializing database...")
    await init_db()
    print("   ✓ Database ready")
    print("   ✓ Rate limiting enabled (10/min, 100/hour)")
    print("   ✓ Response caching enabled (24h TTL)")
    
    yield
    
    # Shutdown
    print("👋 Research Agent API shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Automated Research Agent",
        description="AI-powered research assistant with web search and synthesis",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Configure CORS - must be added BEFORE other middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Add error middleware to ensure CORS headers on errors
    app.add_middleware(CORSErrorMiddleware)

    # Include API routes
    app.include_router(router, prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        loop="asyncio",  # Use asyncio loop to avoid uvloop conflicts
    )