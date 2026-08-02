"""Compatibility ASGI import.

Use `nimbusx.main:app` from the backend directory for new deployments.
"""

try:  # `uvicorn backend.app:app` from the repository root
    from .nimbusx.main import app
except ImportError:  # `uvicorn app:app` from the backend directory
    from nimbusx.main import app


__all__ = ["app"]
