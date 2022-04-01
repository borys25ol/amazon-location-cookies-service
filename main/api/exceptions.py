from typing import List, Optional

from fastapi import FastAPI
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from main.api.utils import form_error_message


class BaseInternalException(Exception):
    """
    Base error class for inherit all internal errors.
    """

    def __init__(
        self, message: str, status_code: int, errors: Optional[List[str]] = None
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.errors = errors


class CookiesNotFoundException(BaseInternalException):
    """
    Exception raised when cookies not extracted for specific `zip_code`.
    """


def add_internal_exception_handler(app: FastAPI) -> None:
    """
    Handle all internal exceptions.
    """

    @app.exception_handler(BaseInternalException)
    async def _exception_handler(
        _: Request, exc: BaseInternalException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "status": exc.status_code,
                "type": type(exc).__name__,
                "message": exc.message,
                "errors": exc.errors or [],
            },
        )


def add_validation_exception_handler(app: FastAPI) -> None:
    """
    Handle `pydantic` validation errors exceptions.
    """

    @app.exception_handler(ValidationError)
    async def _exception_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "status": 422,
                "type": "ValidationError",
                "message": "Schema validation error",
                "errors": form_error_message(errors=exc.errors()),
            },
        )
