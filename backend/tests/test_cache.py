from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pytest

from backend.core.cache import StaleTtlCache


class ManualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_cache(clock: ManualClock) -> StaleTtlCache[str]:
    return StaleTtlCache(
        ttl_seconds=10,
        max_stale_seconds=20,
        retry_seconds=5,
        clock=clock,
    )


def test_cache_hits_until_expiry_then_refreshes() -> None:
    clock = ManualClock()
    cache = make_cache(clock)
    values = iter(["first", "second"])

    assert cache.get(lambda: next(values)) == "first"
    clock.now = 9
    assert cache.get(lambda: next(values)) == "first"
    clock.now = 11
    assert cache.get(lambda: next(values)) == "second"


def test_cache_serves_bounded_stale_value_and_backs_off() -> None:
    clock = ManualClock()
    cache = make_cache(clock)
    calls = 0

    cache.prime("available")
    clock.now = 11

    def unavailable() -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("upstream unavailable")

    assert cache.get(unavailable) == "available"
    assert cache.get(unavailable) == "available"
    assert calls == 1

    clock.now = 31
    with pytest.raises(RuntimeError, match="upstream unavailable"):
        cache.get(unavailable)


def test_cache_refresh_is_single_flight_under_concurrency() -> None:
    clock = ManualClock()
    cache = make_cache(clock)
    calls = 0
    calls_lock = Lock()

    def load() -> str:
        nonlocal calls
        with calls_lock:
            calls += 1
        return "shared"

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: cache.get(load), range(24)))

    assert results == ["shared"] * 24
    assert calls == 1


def test_cache_rejects_invalid_durations() -> None:
    with pytest.raises(ValueError, match="durations"):
        StaleTtlCache[str](
            ttl_seconds=0,
            max_stale_seconds=0,
            retry_seconds=0,
        )
