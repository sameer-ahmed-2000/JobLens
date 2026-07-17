"""
log_context.py — Lightweight correlation ID propagation for cross-module/process tracing.

Usage pattern
-------------
Within a single process/thread, call set_correlation_id() at the entry point of
a unit of work (e.g., when scoring starts for a job, or when the notifier begins
processing a pub/sub message). The CorrelationIdFilter then injects the current
correlation_id into every log record emitted from any logger in that thread.

Cross-process propagation
--------------------------
contextvars are process-local and do NOT cross OS process boundaries.
To trace across processes (e.g., scoring_service → notifier.py), embed the
correlation_id in the shared channel payload (e.g., the Redis pub/sub event dict),
and call set_correlation_id() at the start of each consumer's message handler.
See scoring_service._publish_match_event and notifier.process_message for the
reference implementation.
"""

import logging
import contextvars
from typing import Optional

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current thread/task context."""
    _correlation_id_var.set(cid)


def get_correlation_id() -> str:
    """Return the current correlation ID, or '-' if none is set."""
    return _correlation_id_var.get()


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that injects the current correlation_id into every log record.

    Install on the root logger once at startup (main.py / notifier __main__)
    and update the log format to include %(correlation_id)s:

        format="%(asctime)s [%(levelname)s] %(name)s [cid=%(correlation_id)s] - %(message)s"
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()  # type: ignore[attr-defined]
        return True
