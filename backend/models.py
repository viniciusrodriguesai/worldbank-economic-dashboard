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
