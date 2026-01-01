"""API exception classes and handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error response detail."""
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: ErrorDetail


class APIException(Exception):
    """Base API exception."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict | None = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class UnauthorizedException(APIException):
    """401 Unauthorized exception."""

    def __init__(self, message: str = "Authentication required", code: str = "UNAUTHORIZED"):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(APIException):
    """403 Forbidden exception."""

    def __init__(self, message: str = "Access denied", code: str = "FORBIDDEN"):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundException(APIException):
    """404 Not Found exception."""

    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictException(APIException):
    """409 Conflict exception."""

    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT"):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT
        )


class ValidationException(APIException):
    """422 Validation exception."""

    def __init__(self, message: str = "Validation error", code: str = "VALIDATION_ERROR", details: dict | None = None):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class TooManyRequestsException(APIException):
    """429 Too Many Requests exception."""

    def __init__(self, message: str = "Too many requests", code: str = "RATE_LIMITED"):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class GoneException(APIException):
    """410 Gone exception."""

    def __init__(self, message: str = "Resource no longer available", code: str = "GONE"):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_410_GONE
        )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions from services."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "details": None
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with detailed error information."""
    import logging
    import traceback
    
    logger = logging.getLogger(__name__)
    
    # Log the full traceback for debugging
    logger.error(
        "Unhandled exception: %s\n%s",
        str(exc),
        traceback.format_exc(),
        exc_info=True
    )
    
    # Return error response with exception details
    # In production, you might want to hide the actual error message
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"Internal server error: {str(exc)}",
                "details": {
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc().split('\n')[-5:] if __debug__ else None
                }
            }
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the FastAPI app."""
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(UnauthorizedException, api_exception_handler)
    app.add_exception_handler(ForbiddenException, api_exception_handler)
    app.add_exception_handler(NotFoundException, api_exception_handler)
    app.add_exception_handler(ConflictException, api_exception_handler)
    app.add_exception_handler(ValidationException, api_exception_handler)
    app.add_exception_handler(TooManyRequestsException, api_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    # Add generic exception handler last (it will catch any unhandled exceptions)
    app.add_exception_handler(Exception, generic_exception_handler)
