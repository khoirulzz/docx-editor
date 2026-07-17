import uuid
from typing import Any, Dict, Optional
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    """Base exception for AI DOCX Academic Editor API."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id

    def to_dict(self, request_id: str) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "request_id": self.request_id or request_id
            }
        }

class PreconditionFailedError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="PRECONDITION_FAILED",
            message=message,
            status_code=400,
            details=details
        )

class VersionConflictError(AppException):
    def __init__(self, message: str = "Document version conflict during commit or planning.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VERSION_CONFLICT",
            message=message,
            status_code=409,
            details=details
        )

class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found.",
            status_code=404,
            details=details
        )

class SecurityViolationError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SECURITY_VIOLATION",
            message=message,
            status_code=400,
            details=details
        )

class ArchiveLimitExceededError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="ARCHIVE_LIMIT_EXCEEDED",
            message=message,
            status_code=400,
            details=details
        )

class PlanValidationError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="PLAN_VALIDATION_FAILED",
            message=message,
            status_code=400,
            details=details
        )

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:12]}"
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(req_id)
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:12]}"
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
                "request_id": req_id
            }
        }
    )
