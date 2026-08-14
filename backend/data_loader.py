import logging
import os
import requests
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WB_API_BASE = os.getenv("WB_API_BASE", "https://api.worldbank.org/v2").rstrip("/")
_session = requests.Session()
_session.headers.update({"User-Agent": "worldbank-client/1.0"})
_DEFAULT_TIMEOUT = 10  # segundos


def _fetch_all(path: str, params: dict) -> list:
    """
    Busca todos os registros paginados da API do World Bank.
    """
    records = []
    page = 1
    while True:
        params.update({"format": "json", "per_page": 1000, "page": page})
        url = f"{WB_API_BASE}/{path}"
        try:
            resp = _session.get(url, params=params, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            msg = f"Request error for {url} with params {params}: {e}"
            logger.error(msg)
            raise ValueError(msg)

        data = resp.json()
        if not data or len(data) < 2:
            msg = f"Unexpected API response structure for {url}: {data}"
            logger.error(msg)
            raise ValueError(msg)

        meta, page_data = data[0], data[1]
        records.extend(page_data)
        total_pages = meta.get("pages", 0)
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
            raise ValueError(msg)
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
            raise ValueError(msg)
    logger.info("Indicators dataframe built with %d rows", len(df))
    return df[required_cols]


def get_indicator_data_df(country: str, indicator: str, start: int, end: int) -> pd.DataFrame:
    """
    Busca série histórica de um indicador para um país entre start e end.
    """
    if start > end:
        msg = f"Start year {start} is greater than end year {end}"
        logger.error(msg)
        raise ValueError(msg)
    path = f"country/{country}/indicator/{indicator}"
    try:
        raw = _fetch_all(path, {"date": f"{start}:{end}"})
    except ValueError as e:
        raise ValueError(f"Failed to fetch data for {country}-{indicator} from {start} to {end}: {e}")
    df = pd.json_normalize(raw)
    expected = ['country.value', 'indicator.id', 'date', 'value']
    for col in expected:
        if col not in df.columns:
            msg = f"Expected field '{col}' not found in data for {country}-{indicator}"
            logger.error(msg)
            raise ValueError(msg)
    df = df[expected]
    df.columns = ['country', 'indicator', 'year', 'value']
    df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['year', 'value']).sort_values('year').reset_index(drop=True)
    if df.empty:
        msg = f"No data found for {country}-{indicator} between years {start}-{end}"
        logger.error(msg)
        raise ValueError(msg)
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
        raise ValueError(msg)
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
    result = pd.concat([hist_df, df_fc], ignore_index=True)
    logger.info("Forecast generated for %d future years", years_ahead)
    return result[['country', 'indicator', 'year', 'value']]

