"""Stable API error types and response payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApiProblem(Exception):
    code: str
    message: str
    status_code: int
    details: Any | None = None


class ProviderUnavailable(ApiProblem):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__("provider_unavailable", message, 503, details)


class NotFound(ApiProblem):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__("not_found", f"{resource} '{identifier}' was not found", 404)


class AnalysisNotReady(ApiProblem):
    def __init__(self, identifier: str) -> None:
        super().__init__(
            "analysis_not_ready",
            f"Analysis '{identifier}' has not finished running",
            409,
        )


def error_payload(
    *, code: str, message: str, request_id: str, details: Any | None = None
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if details is not None:
        error["details"] = details
    return {"error": error}
