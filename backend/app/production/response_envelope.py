"""
API response envelope utility for consistent response formatting.

Provides standardized response structure for all API endpoints,
improving client-side error handling and debugging.

Usage:
    from app.production.response_envelope import (
        success_response,
        error_response,
        paginated_response,
        APIResponse
    )

    @app.get("/users/{id}")
    async def get_user(id: str):
        user = await find_user(id)
        return success_response(data=user)

    @app.get("/users")
    async def list_users(page: int = 1, limit: int = 20):
        users, total = await get_users(page, limit)
        return paginated_response(
            data=users,
            page=page,
            limit=limit,
            total=total
        )
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response envelope.

    All API responses follow this structure for consistency.
    """
    success: bool
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        if "timestamp" not in data or not data["timestamp"]:
            data["timestamp"] = datetime.utcnow().isoformat() + "Z"
        super().__init__(**data)


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> JSONResponse:
    """
    Create a successful API response.

    Args:
        data: Response payload
        message: Optional success message
        meta: Optional metadata
        status_code: HTTP status code (default 200)

    Returns:
        JSONResponse with standard envelope
    """
    response_data = {
        "success": True,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if message:
        response_data["message"] = message

    if meta:
        response_data["meta"] = meta

    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def created_response(
    data: Any = None,
    message: str = "Resource created successfully",
    meta: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a response for successful resource creation (201)."""
    return success_response(
        data=data,
        message=message,
        meta=meta,
        status_code=201
    )


def no_content_response() -> JSONResponse:
    """Create a 204 No Content response."""
    return JSONResponse(content=None, status_code=204)


def error_response(
    message: str,
    code: str = "ERROR",
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
    errors: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create an error API response.

    Args:
        message: Human-readable error message
        code: Machine-readable error code
        status_code: HTTP status code
        details: Additional error details
        errors: List of field-specific errors
        request_id: Request ID for tracing

    Returns:
        JSONResponse with error envelope
    """
    error_data = {
        "code": code,
        "message": message,
    }

    if details:
        error_data["details"] = details

    if errors:
        error_data["errors"] = [e.dict() for e in errors]

    response_data = {
        "success": False,
        "error": error_data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if request_id:
        response_data["meta"] = {"request_id": request_id}

    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def validation_error_response(
    errors: List[Dict[str, Any]],
    message: str = "Validation failed",
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a validation error response (422).

    Args:
        errors: List of validation errors from Pydantic
        message: Overall error message
        request_id: Request ID for tracing
    """
    formatted_errors = []
    for error in errors:
        formatted_errors.append(ErrorDetail(
            code="VALIDATION_ERROR",
            message=error.get("msg", "Invalid value"),
            field=".".join(str(loc) for loc in error.get("loc", [])),
            details={"type": error.get("type")}
        ))

    return error_response(
        message=message,
        code="VALIDATION_ERROR",
        status_code=422,
        errors=formatted_errors,
        request_id=request_id
    )


def not_found_response(
    resource: str = "Resource",
    identifier: Optional[str] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a 404 Not Found response."""
    message = f"{resource} not found"
    if identifier:
        message = f"{resource} '{identifier}' not found"

    return error_response(
        message=message,
        code="NOT_FOUND",
        status_code=404,
        request_id=request_id
    )


def unauthorized_response(
    message: str = "Authentication required",
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a 401 Unauthorized response."""
    return error_response(
        message=message,
        code="UNAUTHORIZED",
        status_code=401,
        request_id=request_id
    )


def forbidden_response(
    message: str = "Access denied",
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a 403 Forbidden response."""
    return error_response(
        message=message,
        code="FORBIDDEN",
        status_code=403,
        request_id=request_id
    )


def rate_limit_response(
    retry_after: int = 60,
    message: str = "Rate limit exceeded",
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a 429 Too Many Requests response."""
    response = error_response(
        message=message,
        code="RATE_LIMITED",
        status_code=429,
        details={"retry_after_seconds": retry_after},
        request_id=request_id
    )
    response.headers["Retry-After"] = str(retry_after)
    return response


def server_error_response(
    message: str = "Internal server error",
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a 500 Internal Server Error response."""
    return error_response(
        message=message,
        code="INTERNAL_ERROR",
        status_code=500,
        request_id=request_id
    )


def paginated_response(
    data: List[Any],
    page: int,
    limit: int,
    total: int,
    additional_meta: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create a paginated list response.

    Args:
        data: List of items for current page
        page: Current page number (1-based)
        limit: Items per page
        total: Total items across all pages
        additional_meta: Extra metadata to include

    Returns:
        JSONResponse with pagination metadata
    """
    total_pages = (total + limit - 1) // limit if limit > 0 else 0

    pagination = PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

    meta = {
        "pagination": pagination.dict()
    }

    if additional_meta:
        meta.update(additional_meta)

    return success_response(data=data, meta=meta)


# Exception handlers for FastAPI

class APIError(HTTPException):
    """
    Custom API exception with structured error response.

    Usage:
        raise APIError(
            status_code=400,
            code="INVALID_INPUT",
            message="Email format is invalid",
            details={"field": "email"}
        )
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str = "ERROR",
        details: Optional[Dict[str, Any]] = None,
        errors: Optional[List[ErrorDetail]] = None
    ):
        self.code = code
        self.message = message
        self.details = details
        self.errors = errors
        super().__init__(status_code=status_code, detail=message)


def api_error_handler(request, exc: APIError) -> JSONResponse:
    """
    Exception handler for APIError.

    Register with FastAPI:
        app.add_exception_handler(APIError, api_error_handler)
    """
    from app.production.request_tracking import get_request_id

    return error_response(
        message=exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
        errors=exc.errors,
        request_id=get_request_id()
    )


def http_error_handler(request, exc: HTTPException) -> JSONResponse:
    """
    Exception handler for standard HTTPException.

    Maps HTTP exceptions to standard response format.
    """
    from app.production.request_tracking import get_request_id

    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    return error_response(
        message=str(exc.detail),
        code=code_map.get(exc.status_code, "ERROR"),
        status_code=exc.status_code,
        request_id=get_request_id()
    )


def generic_error_handler(request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler for unhandled errors.

    Logs the error and returns a generic server error response.
    Does NOT expose internal error details to clients.
    """
    from app.production.request_tracking import get_request_id
    from loguru import logger

    request_id = get_request_id()

    logger.exception(
        f"Unhandled exception [request_id={request_id}]: {exc}"
    )

    return server_error_response(
        message="An unexpected error occurred. Please try again later.",
        request_id=request_id
    )


# Response model helpers for OpenAPI documentation

def create_response_model(data_model: type) -> Dict[str, Any]:
    """
    Create OpenAPI response schema for a data model.

    Usage in endpoint:
        @app.get(
            "/users/{id}",
            responses={
                200: create_response_model(UserResponse),
                404: error_response_schema("User not found")
            }
        )
    """
    return {
        "model": APIResponse[data_model],
        "description": "Successful response"
    }


def error_response_schema(description: str) -> Dict[str, Any]:
    """Create OpenAPI schema for error response."""
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                            }
                        },
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                }
            }
        }
    }
