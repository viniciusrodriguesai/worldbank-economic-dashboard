from pydantic import BaseModel, ConfigDict


class Country(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    iso2Code: str
    name: str
    region: str
    capitalCity: str


class Indicator(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str


class IndicatorPoint(BaseModel):
    country: str
    indicator: str
    year: int
    value: float


class ForecastPoint(IndicatorPoint):
    lower_bound: float
    upper_bound: float


class ForecastMetrics(BaseModel):
    mae: float
    rmse: float
    mape: float | None = None
    smape: float | None = None


class ModelEvaluation(BaseModel):
    selected_model: str
    selected_order: tuple[int, int, int] | None = None
    validation_points: int
    model_metrics: ForecastMetrics
    baseline_model: str
    baseline_metrics: ForecastMetrics
    beats_baseline: bool


class ForecastResponse(BaseModel):
    history: list[IndicatorPoint]
    forecast: list[ForecastPoint]
    evaluation: ModelEvaluation
    horizon: int
    missing_years: list[int]
    warnings: list[str]
