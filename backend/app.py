import logging
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Tuple
from backend.data_loader import (
    get_countries_df,
    get_indicators_df,
    get_indicator_data_df,
    forecast_indicator
)
from backend.models import Country, Indicator, IndicatorPoint
import uvicorn

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="World Bank Economic Dashboard API",
    version="1.0.0"
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Simple TTL caches
_indicators_cache: Optional[List[dict]] = None
_countries_cache: Optional[List[dict]] = None
_cache_timestamp: Optional[float] = None
_CACHE_TTL = 3600  # seconds

@app.on_event("startup")
async def load_caches():
    """
    Preload countries and indicators at startup
    and refresh caches when TTL expires.
    """
    await _refresh_caches()

async def _refresh_caches():
    import time
    global _indicators_cache, _countries_cache, _cache_timestamp
    try:
        logger.info("Refreshing caches...")
        df_ind = get_indicators_df()
        _indicators_cache = df_ind.to_dict(orient="records")
        df_countries = get_countries_df()
        _countries_cache = df_countries.to_dict(orient="records")
        _cache_timestamp = time.time()
        logger.info(f"Cache loaded: {len(_countries_cache)} countries and {len(_indicators_cache)} indicators")
    except Exception as e:
        logger.error(f"Error preloading cache: {e}", exc_info=True)


def _ensure_cache_valid():
    import time, asyncio
    if _cache_timestamp is None or (time.time() - _cache_timestamp) > _CACHE_TTL:
        asyncio.run(_refresh_caches())

@app.get("/countries", response_model=List[Country])
def countries():
    """Return the list of countries, cached if available."""
    try:
        _ensure_cache_valid()
        return _countries_cache or []
    except Exception as e:
        logger.exception("Failed to fetch countries cache")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve country list: {e}")

@app.get("/indicators", response_model=List[Indicator])
def indicators():
    """Return the list of indicators, cached if available."""
    try:
        _ensure_cache_valid()
        return _indicators_cache or []
    except Exception as e:
        logger.exception("Failed to fetch indicators cache")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve indicator list: {e}")

@app.get("/data", response_model=List[IndicatorPoint])
def data(
    country: str = Query(..., min_length=3, max_length=3, description="ISO3 country code"),
    indicator: str = Query(..., min_length=1, description="Indicator code"),
    start: int = Query(2000, ge=1900, le=2100, description="Start year"),
    end: int = Query(2022, ge=1900, le=2100, description="End year")
):
    """Return time series data for a given country and indicator."""
    if start > end:
        raise HTTPException(status_code=400, detail="Start year cannot be greater than end year.")
    try:
        df = get_indicator_data_df(country, indicator, start, end)
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for country='{country}', indicator='{indicator}' in {start}-{end}"
            )
        return df.to_dict(orient="records")
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"ValueError in /data for country={country}, indicator={indicator}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error in /data for country={country}, indicator={indicator}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while fetching data for country='{country}', indicator='{indicator}'."
        )

@app.get("/forecast", response_model=List[IndicatorPoint])
def forecast(
    country: str = Query(..., min_length=3, max_length=3, description="ISO3 country code"),
    indicator: str = Query(..., min_length=1, description="Indicator code"),
    start: int = Query(1960, ge=1900, le=2100, description="Start year for model fitting"),
    end: Optional[int] = Query(None, ge=1900, le=2100, description="End year for model fitting"),
    years_ahead: int = Query(5, ge=1, le=50, description="Years to forecast ahead"),
    arima_order: Optional[Tuple[int,int,int]] = Query((1,1,1), description="ARIMA order (p,d,q)")
):
    """Return forecast data based on an ARIMA model for a given country and indicator."""
    try:
        from datetime import datetime
        if end is None:
            end = datetime.now().year
        if start > end:
            raise HTTPException(status_code=400, detail="Start year cannot be greater than end year.")
        df_fc = forecast_indicator(country, indicator, start, end, years_ahead, arima_order)
        if df_fc.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Forecast not available for country='{country}', indicator='{indicator}' with provided data."
            )
        return df_fc.to_dict(orient="records")
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"ValueError in /forecast for country={country}, indicator={indicator}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Forecast feature not yet implemented.")
    except Exception as e:
        logger.exception(f"Unexpected error in /forecast for country={country}, indicator={indicator}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during forecasting for country='{country}', indicator='{indicator}'."
        )

if __name__ == "__main__":
    # Run with: uvicorn backend.app:app --reload
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
