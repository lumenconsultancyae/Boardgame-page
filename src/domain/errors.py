"""Domain exceptions and structured error codes."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Canonical error codes returned in API error envelopes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DomainError(Exception):
    """Base exception for all domain and application rule violations."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details: dict[str, Any] = details or {}


class ValidationError(DomainError):
    """Raised when input data violates domain invariants."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code=ErrorCode.VALIDATION_ERROR, details=details)


class NotFoundError(DomainError):
    """Raised when a requested boardgame, session, or event does not exist."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code=ErrorCode.NOT_FOUND, details=details)
