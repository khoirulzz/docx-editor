import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.errors import AppException, app_exception_handler, generic_exception_handler
from app.api.sessions import router as sessions_router
from app.api.references import router as references_router
from app.api.proposals import router as proposals_router
from app.api.versions import router as versions_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router

app = FastAPI(
    title="AI DOCX Academic Editor API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for external UI hosting (Cloudflare Pages, Vercel, localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.api_route("/", methods=["GET", "HEAD"], tags=["root"])
async def root():
    """Root endpoint returning API status, documentation links, and capabilities."""
    return {
        "app": "AI DOCX Academic Editor API",
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "health_check": "/health",
        "endpoints": {
            "create_session": "POST /v1/sessions",
            "chat_planning": "POST /v1/sessions/{session_id}/chat",
            "get_session": "GET /v1/sessions/{session_id}",
            "get_graph": "GET /v1/sessions/{session_id}/graph",
            "commit_proposal": "POST /v1/sessions/{session_id}/proposals/{proposal_id}/commit",
            "export_version": "GET /v1/sessions/{session_id}/versions/{version}/export"
        }
    }

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint required by Milestone 0 exit condition."""
    return {"status": "ok", "version": "1.0.0", "env": settings.APP_ENV}

# Include API routers under /v1 prefix
app.include_router(sessions_router, prefix="/v1")
app.include_router(references_router, prefix="/v1")
app.include_router(proposals_router, prefix="/v1")
app.include_router(versions_router, prefix="/v1")
app.include_router(chat_router, prefix="/v1")
