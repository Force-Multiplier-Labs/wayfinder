"""
TraceContext extraction middleware for A2A HTTP servers.

Provides middleware for both Flask and FastAPI that extracts W3C TraceContext
(traceparent, tracestate) and Baggage headers from inbound requests, starts
a SERVER span with the extracted parent, and cleans up on response.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from opentelemetry import context, trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind, Status, StatusCode

logger = logging.getLogger(__name__)


def _get_tracer() -> trace.Tracer:
    """Get or create a tracer for A2A middleware."""
    return trace.get_tracer("contextcore.a2a.middleware")


# ---------------------------------------------------------------------------
# Flask middleware
# ---------------------------------------------------------------------------

def add_flask_trace_middleware(app: Any) -> None:
    """
    Add TraceContext extraction middleware to a Flask app.

    Extracts traceparent/tracestate/baggage from incoming request headers,
    starts a SERVER span with the extracted parent context, and ends it
    after the response is sent.

    Args:
        app: A Flask application instance.
    """
    try:
        from flask import g, request
    except ImportError:
        logger.warning("Flask not available; skipping trace middleware")
        return

    tracer = _get_tracer()

    @app.before_request
    def _start_server_span() -> None:
        # Extract propagated context from incoming headers
        carrier = dict(request.headers)
        extracted_ctx = extract(carrier)

        # Start a SERVER span parented to the extracted context
        span = tracer.start_span(
            name=f"{request.method} {request.path}",
            kind=SpanKind.SERVER,
            context=extracted_ctx,
            attributes={
                "http.request.method": request.method,
                "url.path": request.path,
            },
        )

        # Attach the new context (with span) so downstream code sees it
        token = context.attach(trace.set_span_in_context(span, extracted_ctx))
        g._otel_span = span
        g._otel_token = token

    @app.after_request
    def _end_server_span(response: Any) -> Any:
        span = getattr(g, "_otel_span", None)
        token = getattr(g, "_otel_token", None)

        if span is not None:
            span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
            else:
                span.set_status(Status(StatusCode.OK))
            span.end()

        if token is not None:
            context.detach(token)

        return response


# ---------------------------------------------------------------------------
# FastAPI / ASGI middleware
# ---------------------------------------------------------------------------

class TraceContextMiddleware:
    """
    ASGI middleware for FastAPI that extracts W3C TraceContext and Baggage
    from inbound HTTP headers and wraps each request in a SERVER span.
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self.tracer = _get_tracer()

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Build a carrier dict from ASGI headers
        headers = dict(scope.get("headers", []))
        carrier = {
            k.decode("utf-8") if isinstance(k, bytes) else k:
            v.decode("utf-8") if isinstance(v, bytes) else v
            for k, v in headers.items()
        }

        extracted_ctx = extract(carrier)
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        span = self.tracer.start_span(
            name=f"{method} {path}",
            kind=SpanKind.SERVER,
            context=extracted_ctx,
            attributes={
                "http.request.method": method,
                "url.path": path,
            },
        )
        token = context.attach(trace.set_span_in_context(span, extracted_ctx))

        try:
            await self.app(scope, receive, send)
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
        finally:
            span.end()
            context.detach(token)
