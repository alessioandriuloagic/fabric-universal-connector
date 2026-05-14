from __future__ import annotations
import time
import logging
from typing import Callable, TypeVar

from agic_fabric_connector.base.exceptions import ThrottlingError, TransientError

T = TypeVar("T")
logger = logging.getLogger(__name__)


def with_retry(
    fn: Callable[[], T],
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except ThrottlingError as e:
            delay = e.retry_after_seconds or base_delay_seconds * (backoff_multiplier ** (attempt - 1))
            logger.warning("Throttled on attempt %d/%d — retrying in %.1fs", attempt, max_attempts, delay)
            time.sleep(delay)
            last_error = e
        except TransientError as e:
            delay = base_delay_seconds * (backoff_multiplier ** (attempt - 1))
            logger.warning("Transient error on attempt %d/%d — retrying in %.1fs: %s", attempt, max_attempts, delay, e)
            time.sleep(delay)
            last_error = e
    raise last_error  # type: ignore[misc]
