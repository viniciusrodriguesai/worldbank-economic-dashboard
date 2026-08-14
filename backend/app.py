import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from threading import BoundedSemaphore, Lock
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from backend.data_loader import (
    forecast_indicator,
    get_countries_df,
    get_indicator_data_df,
    get_indicators_df,
)
from backend.exceptions import (
    ForecastUnavailableError,
    InvalidRequestError,
    UpstreamConnectionError,
    UpstreamResponseError,
    UpstreamTimeoutError,
)
from backend.models import Country, ForecastResponse, Indicator, IndicatorPoint
from backend.services.forecasting import evaluate_forecast

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await run_in_threadpool(_ensure_cache_valid)
    except Exception:
        logger.exception("Unable to preload metadata cache")
    yield


app = FastAPI(
    title="World Bank Economic Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

def _cors_origins() -> list[str]:
    origins = [
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            origin == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise RuntimeError(
                "CORS_ORIGINS must contain exact HTTP(S) origins without credentials or paths."
            )
    return origins


allowed_origins = _cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)

# Simple TTL caches
_indicators_cache: list[dict] | None = None
_countries_cache: list[dict] | None = None
_cache_timestamp: float | None = None
_CACHE_TTL = 3600  # seconds
_cache_lock = Lock()
_forecast_slots = BoundedSemaphore(value=2)

def _refresh_caches():
    global _indicators_cache, _countries_cache, _cache_timestamp
    logger.info("Refreshing metadata cache")
    indicators = get_indicators_df().to_dict(orient="records")
    countries = get_countries_df().to_dict(orient="records")
    _indicators_cache = indicators
    _countries_cache = countries
    _cache_timestamp = time.monotonic()
    logger.info(
        "Cache loaded: %d countries and %d indicators",
        len(countries),
        len(indicators),
    )


def _ensure_cache_valid():
    cache_is_fresh = (
        _cache_timestamp is not None
        and (time.monotonic() - _cache_timestamp) <= _CACHE_TTL
    )
    if cache_is_fresh:
        return

    with _cache_lock:
        cache_is_fresh = (
            _cache_timestamp is not None
            and (time.monotonic() - _cache_timestamp) <= _CACHE_TTL
        )
        if not cache_is_fresh:
            _refresh_caches()

@app.get("/countries", response_model=list[Country])
def countries():
    """Return the list of countries, cached if available."""
    try:
        _ensure_cache_valid()
        return _countries_cache or []
    except Exception as e:
        logger.exception("Failed to fetch countries cache")
        raise HTTPException(
            status_code=503,
            detail="Country data is temporarily unavailable.",
        ) from e

@app.get("/indicators", response_model=list[Indicator])
def indicators(
    search: str | None = Query(None, max_length=100, pattern=r"^[^\x00-\x1f\x7f]*$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=50_000),
):
    """Return a bounded, searchable slice of cached indicator metadata."""
    try:
        _ensure_cache_valid()
        available = _indicators_cache or []
        if search:
            term = search.casefold().strip()
            available = [
                item
                for item in available
                if term in str(item.get("name", "")).casefold()
                or term in str(item.get("id", "")).casefold()
            ]
        return available[offset : offset + limit]
    except Exception as e:
        logger.exception("Failed to fetch indicators cache")
        raise HTTPException(
            status_code=503,
            detail="Indicator data is temporarily unavailable.",
        ) from e

def _validate_known_codes(country: str, indicator: str) -> None:
    try:
        _ensure_cache_valid()
    except Exception as exc:
        logger.exception("Unable to validate metadata")
        raise HTTPException(status_code=503, detail="Metadata is temporarily unavailable.") from exc
    if not any(item.get("id") == country for item in (_countries_cache or [])):
        raise HTTPException(status_code=422, detail="Unknown country code.")
    if not any(item.get("id") == indicator for item in (_indicators_cache or [])):
        raise HTTPException(status_code=422, detail="Unknown indicator code.")


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, InvalidRequestError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, UpstreamTimeoutError):
        raise HTTPException(status_code=504, detail="World Bank API request timed out.") from exc
    if isinstance(exc, UpstreamConnectionError):
        raise HTTPException(status_code=503, detail="World Bank API is temporarily unavailable.") from exc
    if isinstance(exc, UpstreamResponseError):
        raise HTTPException(status_code=502, detail="World Bank API returned an invalid response.") from exc
    if isinstance(exc, ForecastUnavailableError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


@app.get("/data", response_model=list[IndicatorPoint])
def data(
    country: str = Query(..., pattern=r"^[A-Z]{3}$", description="ISO3 country code"),
    indicator: str = Query(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        description="World Bank indicator code",
    ),
    start: int = Query(2000, ge=1900, le=2100, description="Start year"),
    end: int = Query(datetime.now(UTC).year, ge=1900, le=datetime.now(UTC).year + 1),
):
    """Return time series data for a given country and indicator."""
    if start > end:
        raise HTTPException(status_code=400, detail="Start year cannot be greater than end year.")
    if end - start > 120:
        raise HTTPException(status_code=422, detail="Requested period cannot exceed 120 years.")
    _validate_known_codes(country, indicator)
    try:
        df = get_indicator_data_df(country, indicator, start, end)
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail="No data was found for the selected country, indicator, and period."
            )
        return df.to_dict(orient="records")
    except HTTPException:
        raise
    except (InvalidRequestError, UpstreamTimeoutError, UpstreamConnectionError, UpstreamResponseError) as exc:
        _raise_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error while loading economic data")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while loading data."
        ) from exc


@app.get("/data/compare", response_model=list[IndicatorPoint])
def compare_data(
    countries: Annotated[list[str], Query(description="One to five ISO3 country codes")],
    indicator: str = Query(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
    start: int = Query(2000, ge=1900, le=2100),
    end: int = Query(datetime.now(UTC).year, ge=1900, le=datetime.now(UTC).year + 1),
):
    """Return one shared indicator for a bounded set of countries."""
    if not 1 <= len(countries) <= 5:
        raise HTTPException(status_code=422, detail="Select between one and five countries.")
    if len(set(countries)) != len(countries):
        raise HTTPException(status_code=422, detail="Country codes must be unique.")
    if any(len(code) != 3 or not code.isascii() or not code.isupper() for code in countries):
        raise HTTPException(status_code=422, detail="Country codes must be uppercase ISO3 values.")
    if start > end:
        raise HTTPException(status_code=400, detail="Start year cannot be greater than end year.")
    if end - start > 120:
        raise HTTPException(status_code=422, detail="Requested period cannot exceed 120 years.")
    records: list[dict] = []
    try:
        for country in countries:
            _validate_known_codes(country, indicator)
            frame = get_indicator_data_df(country, indicator, start, end)
            if not frame.empty:
                frame = frame.assign(country=country)
                records.extend(frame.to_dict(orient="records"))
    except HTTPException:
        raise
    except (InvalidRequestError, UpstreamTimeoutError, UpstreamConnectionError, UpstreamResponseError) as exc:
        _raise_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error while loading comparison data")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while loading comparison data.",
        ) from exc
    if not records:
        raise HTTPException(status_code=404, detail="No comparison data was found.")
    return records

@app.get("/forecast", response_model=list[IndicatorPoint])
def forecast(
    country: str = Query(..., pattern=r"^[A-Z]{3}$", description="ISO3 country code"),
    indicator: str = Query(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        description="World Bank indicator code",
    ),
    start: int = Query(1960, ge=1900, le=2100, description="Start year for model fitting"),
    end: int | None = Query(None, ge=1900, le=datetime.now(UTC).year + 1),
    years_ahead: int = Query(5, ge=1, le=10, description="Years to forecast ahead"),
):
    """Return forecast data based on an ARIMA model for a given country and indicator."""
    try:
        if end is None:
            end = datetime.now(UTC).year
        if start > end:
            raise HTTPException(status_code=400, detail="Start year cannot be greater than end year.")
        if end - start > 120:
            raise HTTPException(status_code=422, detail="Requested period cannot exceed 120 years.")
        _validate_known_codes(country, indicator)
        if not _forecast_slots.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="Forecast capacity is busy. Please retry shortly.")
        try:
            df_fc = forecast_indicator(country, indicator, start, end, years_ahead)
        finally:
            _forecast_slots.release()
        if df_fc.empty:
            raise HTTPException(
                status_code=404,
                detail="Forecast is not available for the selected series."
            )
        return df_fc.to_dict(orient="records")
    except HTTPException:
        raise
    except (
        ForecastUnavailableError,
        InvalidRequestError,
        UpstreamTimeoutError,
        UpstreamConnectionError,
        UpstreamResponseError,
    ) as exc:
        _raise_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error during forecasting")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating the forecast."
        ) from exc


@app.get("/forecast/evaluate", response_model=ForecastResponse)
def forecast_evaluation(
    country: str = Query(..., pattern=r"^[A-Z]{3}$"),
    indicator: str = Query(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
    start: int = Query(1960, ge=1900, le=2100),
    end: int | None = Query(None, ge=1900, le=datetime.now(UTC).year + 1),
    years_ahead: int = Query(5, ge=1, le=10),
):
    """Return a temporally validated forecast, metrics, intervals, and warnings."""
    resolved_end = end if end is not None else datetime.now(UTC).year
    if start > resolved_end:
        raise HTTPException(status_code=400, detail="Start year cannot be greater than end year.")
    if resolved_end - start > 120:
        raise HTTPException(status_code=422, detail="Requested period cannot exceed 120 years.")
    _validate_known_codes(country, indicator)
    if not _forecast_slots.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Forecast capacity is busy. Please retry shortly.")
    try:
        frame = get_indicator_data_df(country, indicator, start, resolved_end)
        if frame.empty:
            raise HTTPException(status_code=404, detail="Forecast history is not available.")
        return evaluate_forecast(frame, country, indicator, years_ahead)
    except HTTPException:
        raise
    except (
        ForecastUnavailableError,
        InvalidRequestError,
        UpstreamTimeoutError,
        UpstreamConnectionError,
        UpstreamResponseError,
    ) as exc:
        _raise_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error during evaluated forecasting")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating the forecast.",
        ) from exc
    finally:
        _forecast_slots.release()
