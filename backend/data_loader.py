import logging
import os
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import requests
from statsmodels.tsa.arima.model import ARIMA

from backend.exceptions import (
    ForecastUnavailableError,
    InvalidRequestError,
    UpstreamConnectionError,
    UpstreamResponseError,
    UpstreamTimeoutError,
)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WB_API_BASE = os.getenv("WB_API_BASE", "https://api.worldbank.org/v2").rstrip("/")
_session = requests.Session()
_session.headers.update({"User-Agent": "worldbank-client/1.0"})
_DEFAULT_TIMEOUT = (3.05, 10)
_MAX_PAGES = 100
_MAX_RECORDS = 100_000
_MAX_PAGE_BYTES = 10_000_000
_COUNTRY_PATTERN = re.compile(r"^[A-Z]{3}$")
_INDICATOR_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _validate_api_base(value: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("WB_API_BASE must be a credential-free HTTPS URL.")


_validate_api_base(WB_API_BASE)


def validate_series_request(country: str, indicator: str, start: int, end: int) -> None:
    """Validate identifiers before they can influence an upstream path."""
    if not _COUNTRY_PATTERN.fullmatch(country):
        raise InvalidRequestError("Country must be a three-letter uppercase code.")
    if not _INDICATOR_PATTERN.fullmatch(indicator):
        raise InvalidRequestError("Indicator code has an invalid format.")
    current_year = datetime.now(UTC).year
    if start < 1900 or end > current_year + 1:
        raise InvalidRequestError("Requested years are outside the supported range.")
    if start > end:
        raise InvalidRequestError("Start year cannot be greater than end year.")
    if end - start > 120:
        raise InvalidRequestError("Requested period cannot exceed 120 years.")


def _fetch_all(path: str, params: dict[str, object]) -> list[dict]:
    """
    Busca todos os registros paginados da API do World Bank.
    """
    records: list[dict] = []
    page = 1
    while True:
        request_params = {**params, "format": "json", "per_page": 1000, "page": page}
        url = f"{WB_API_BASE}/{path}"
        try:
            resp = _session.get(
                url,
                params=request_params,
                timeout=_DEFAULT_TIMEOUT,
                allow_redirects=False,
            )
            if 300 <= resp.status_code < 400:
                raise UpstreamResponseError("World Bank redirects are not accepted.")
            resp.raise_for_status()
        except UpstreamResponseError:
            raise
        except requests.exceptions.Timeout as exc:
            logger.warning("World Bank request timed out for %s", path.split("/")[0])
            raise UpstreamTimeoutError("World Bank request timed out.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.warning("World Bank connection failed for %s", path.split("/")[0])
            raise UpstreamConnectionError("World Bank API is unavailable.") from exc
        except requests.exceptions.RequestException as exc:
            logger.warning("World Bank returned an unsuccessful HTTP response")
            raise UpstreamResponseError("World Bank request failed.") from exc

        if len(resp.content) > _MAX_PAGE_BYTES:
            raise UpstreamResponseError("World Bank response exceeded the safe size limit.")
        try:
            data = resp.json()
        except (requests.exceptions.JSONDecodeError, ValueError) as exc:
            logger.warning("World Bank returned malformed JSON")
            raise UpstreamResponseError("World Bank returned malformed JSON.") from exc
        if not isinstance(data, list) or len(data) < 2:
            logger.warning("World Bank returned an unexpected response envelope")
            raise UpstreamResponseError("World Bank returned an unexpected response.")

        meta, page_data = data[0], data[1]
        if not isinstance(meta, dict) or not isinstance(page_data, list):
            raise UpstreamResponseError("World Bank returned an unexpected response.")
        if not all(isinstance(record, dict) for record in page_data):
            raise UpstreamResponseError("World Bank returned invalid records.")
        records.extend(page_data)
        if len(records) > _MAX_RECORDS:
            raise UpstreamResponseError("World Bank response exceeded the record limit.")
        total_pages = meta.get("pages")
        if total_pages == 0 and not page_data:
            break
        if not isinstance(total_pages, int) or not 1 <= total_pages <= _MAX_PAGES:
            raise UpstreamResponseError("World Bank pagination metadata is invalid.")
        if page >= total_pages:
            break
        page += 1
    logger.info(f"Fetched {len(records)} records from {path}")
    return records


def get_countries_df() -> pd.DataFrame:
    """
    Busca lista de países disponíveis no World Bank.
    """
    raw = _fetch_all("country", {})
    df = pd.json_normalize(raw)
    required_cols = ['id', 'iso2Code', 'name', 'region.value', 'capitalCity']
    for col in required_cols:
        if col not in df.columns:
            msg = f"Expected field '{col}' not found in countries data"
            logger.error(msg)
            raise UpstreamResponseError("World Bank country metadata is incomplete.")
    logger.info("Countries dataframe built with %d rows", len(df))
    return df[required_cols].rename(columns={"region.value": "region"})


def get_indicators_df() -> pd.DataFrame:
    """
    Busca lista de indicadores.
    """
    raw = _fetch_all("indicator", {})
    df = pd.json_normalize(raw)
    required_cols = ['id', 'name']
    for col in required_cols:
        if col not in df.columns:
            msg = f"Expected field '{col}' not found in indicators data"
            logger.error(msg)
            raise UpstreamResponseError("World Bank indicator metadata is incomplete.")
    logger.info("Indicators dataframe built with %d rows", len(df))
    return df[required_cols]


def get_indicator_data_df(country: str, indicator: str, start: int, end: int) -> pd.DataFrame:
    """
    Busca série histórica de um indicador para um país entre start e end.
    """
    validate_series_request(country, indicator, start, end)
    path = f"country/{country}/indicator/{indicator}"
    raw = _fetch_all(path, {"date": f"{start}:{end}"})
    df = pd.json_normalize(raw)
    expected = ['country.value', 'indicator.id', 'date', 'value']
    for col in expected:
        if col not in df.columns:
            msg = f"Expected field '{col}' not found in data for {country}-{indicator}"
            logger.error(msg)
            raise UpstreamResponseError("World Bank data is missing required fields.")
    df = df[expected]
    df.columns = ['country', 'indicator', 'year', 'value']
    df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['year', 'value'])
    df = df[np.isfinite(df['value'])]
    if df['year'].duplicated().any():
        raise UpstreamResponseError("World Bank returned duplicate annual observations.")
    df = df.sort_values('year').reset_index(drop=True)
    if df.empty:
        logger.info(
            "No data found for %s-%s between years %d-%d",
            country,
            indicator,
            start,
            end,
        )
        return df
    logger.info("Data for %s - %s from %d to %d: %d records", country, indicator, start, end, len(df))
    return df


def forecast_indicator(country: str, indicator: str, start: int, end: int,
                       years_ahead: int, arima_order: tuple = (1, 1, 1)) -> pd.DataFrame:
    """
    Ajusta ARIMA à série histórica e prevê anos à frente.
    """
    hist_df = get_indicator_data_df(country, indicator, start, end)
    series = hist_df.set_index('year')['value']
    if len(series) < 10:
        msg = f"Series too short ({len(series)} points) for ARIMA; minimum 10 points required"
        logger.error(msg)
        raise ForecastUnavailableError("At least 10 observations are required for forecasting.")
    logger.info("Fitting ARIMA(order=%s) for %s-%s", arima_order, country, indicator)
    model = ARIMA(series, order=arima_order)
    fitted = model.fit()
    forecast_vals = fitted.forecast(steps=years_ahead)
    last_year = int(series.index.max())
    fc_years = list(range(last_year + 1, last_year + years_ahead + 1))
    df_fc = pd.DataFrame({
        'country': country,
        'indicator': indicator,
        'year': fc_years,
        'value': forecast_vals.values
    })
    logger.info("Forecast generated for %d future years", years_ahead)
    return df_fc[['country', 'indicator', 'year', 'value']]

