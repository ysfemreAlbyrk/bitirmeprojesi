"""Dedicated API request logger for external service calls.

Logs every outgoing request to a separate file (logs/api_requests.log)
so that API traffic can be audited independently of application logs.
"""
import logging
import os
import time
from datetime import datetime
from typing import Optional

# Ensure log directory exists
os.makedirs("logs", exist_ok=True)

_api_request_logger: Optional[logging.Logger] = None


def _get_logger() -> logging.Logger:
    """Lazy-initialize the dedicated API-request logger."""
    global _api_request_logger
    if _api_request_logger is not None:
        return _api_request_logger

    logger = logging.getLogger("vibetale_api_requests")
    logger.setLevel(logging.INFO)
    # Prevent propagation to root logger so we don't duplicate lines
    logger.propagate = False

    # Only add the file handler once
    if not logger.handlers:
        handler = logging.FileHandler(
            "logs/api_requests.log",
            mode="a",
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    _api_request_logger = logger
    return _api_request_logger


def log_api_request(
    service: str,
    operation: str,
    status: str,
    duration_ms: float = 0.0,
    details: str = "",
):
    """Write a single API request record to the dedicated log file.

    Args:
        service: Human-readable service name (e.g. 'Gemini', 'Clipdrop').
        operation: What was requested (e.g. 'generate_content', 'POST /text-to-image/v1').
        status: Result summary (e.g. '200 OK', 'error', 'timeout').
        duration_ms: Round-trip time in milliseconds.
        details: Optional extra info (truncated to 200 chars to keep lines short).
    """
    logger = _get_logger()
    safe_details = (details[:200] + "…") if len(details) > 200 else details
    safe_details = safe_details.replace("\n", " ").replace("\r", "")
    logger.info(
        f"{service} | {operation} | {status} | {duration_ms:.1f}ms | {safe_details}"
    )


class ApiCallTimer:
    """Context manager / decorator helper that measures duration and logs the call."""

    def __init__(self, service: str, operation: str, details: str = ""):
        self.service = service
        self.operation = operation
        self.details = details
        self.start: Optional[float] = None
        self.status = "unknown"

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.perf_counter() - self.start) * 1000 if self.start else 0.0
        if exc_type is not None:
            self.status = f"error: {exc_type.__name__}"
        log_api_request(
            service=self.service,
            operation=self.operation,
            status=self.status,
            duration_ms=elapsed,
            details=self.details,
        )
        return False  # Don't swallow exceptions
