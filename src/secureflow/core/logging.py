"""SecureFlow Structured JSON Logging and Prometheus Metrics.

Ensures compliance with SR-06, TB2, TB3.
"""
import json
import logging
import sys
import time
from typing import Any, Dict
from prometheus_client import Counter, Histogram, Gauge

# Prometheus Metrics Definitions (Canonical Counters)
FAILED_LOGINS_TOTAL = Counter(
    "failed_logins_total",
    "Total count of failed authentication attempts"
)
INVALID_SIGNATURES_TOTAL = Counter(
    "invalid_signatures_total",
    "Total count of rejected HMAC telemetry signatures"
)
REPLAY_ATTEMPTS_TOTAL = Counter(
    "replay_attempts_total",
    "Total count of detected telemetry replay attacks"
)
RATE_LIMIT_HITS_TOTAL = Counter(
    "rate_limit_hits_total",
    "Total count of requests blocked by rate limiting"
)
SUSPICIOUS_TELEMETRY_TOTAL = Counter(
    "suspicious_telemetry_total",
    "Total count of implausible or out-of-range telemetry readings"
)
SIGNAL_CHANGES_TOTAL = Counter(
    "signal_changes_total",
    "Total count of applied signal changes",
    ["status"]
)
EMERGENCY_REQUESTS_TOTAL = Counter(
    "emergency_requests_total",
    "Total count of authorized emergency green corridor requests"
)
ACTIVE_SENSORS_GAUGE = Gauge(
    "active_sensors",
    "Number of active reporting traffic sensors"
)
AUDIT_CHAIN_VALID_GAUGE = Gauge(
    "audit_chain_valid",
    "Status of the tamper-evident audit log hash chain (1=valid, 0=broken)"
)
INGEST_LATENCY_HISTOGRAM = Histogram(
    "ingest_latency_seconds",
    "Latency of telemetry processing in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)


class JSONFormatter(logging.Formatter):
    """Custom structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include contextual fields attached to log records
        for key in ("request_id", "actor", "action", "target", "ip", "client"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure structured JSON logging handler for stdout."""
    logger = logging.getLogger("secureflow")
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    # Configure uvicorn loggers
    for uvi_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvi_logger = logging.getLogger(uvi_logger_name)
        uvi_logger.handlers = []
        uvi_logger.addHandler(handler)

    return logger


logger = setup_logging()
