"""Small thread-safe cache primitives used by the API process."""

from collections.abc import Callable
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar, cast

T = TypeVar("T")
_MISSING = object()


class StaleTtlCache(Generic[T]):
    """Cache a value while preventing refresh storms and bounded outages.

    A previously loaded value may be served for max_stale_seconds after its
    normal TTL when refresh fails. This is deliberately bounded so invalid or
    indefinitely old metadata is never retained forever.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_stale_seconds: float,
        retry_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds <= 0 or max_stale_seconds < 0 or retry_seconds < 0:
            raise ValueError("Cache durations must be positive or zero as applicable.")
        self._ttl_seconds = ttl_seconds
        self._max_stale_seconds = max_stale_seconds
        self._retry_seconds = retry_seconds
        self._clock = clock
        self._value: T | object = _MISSING
        self._loaded_at: float | None = None
        self._retry_after = 0.0
        self._lock = Lock()

    def _has_value(self) -> bool:
        return self._value is not _MISSING and self._loaded_at is not None

    def _is_fresh(self, now: float) -> bool:
        return (
            self._has_value()
            and cast(float, self._loaded_at) + self._ttl_seconds >= now
        )

    def _is_usable_stale(self, now: float) -> bool:
        return (
            self._has_value()
            and cast(float, self._loaded_at)
            + self._ttl_seconds
            + self._max_stale_seconds
            >= now
        )

    def _current(self) -> T:
        return cast(T, self._value)

    def get(self, loader: Callable[[], T]) -> T:
        """Return a fresh value, or bounded stale data if refresh fails."""
        now = self._clock()
        if self._is_fresh(now):
            return self._current()
        if now < self._retry_after and self._is_usable_stale(now):
            return self._current()

        with self._lock:
            now = self._clock()
            if self._is_fresh(now):
                return self._current()
            if now < self._retry_after and self._is_usable_stale(now):
                return self._current()
            try:
                value = loader()
            except Exception:
                if self._is_usable_stale(now):
                    self._retry_after = now + self._retry_seconds
                    return self._current()
                raise
            self._value = value
            self._loaded_at = self._clock()
            self._retry_after = 0.0
            return value

    def prime(self, value: T) -> None:
        """Seed a value explicitly, primarily for deterministic tests."""
        with self._lock:
            self._value = value
            self._loaded_at = self._clock()
            self._retry_after = 0.0

    def clear(self) -> None:
        """Remove the cached value safely."""
        with self._lock:
            self._value = _MISSING
            self._loaded_at = None
            self._retry_after = 0.0
