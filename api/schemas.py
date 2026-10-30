"""Request and response models shared by the MySQL and MongoDB endpoints.

Both databases expose the same record shape so clients can switch backends
by changing only the URL prefix (/sql or /mongo).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class Indicators(BaseModel):
    ma_20: float | None = None
    ma_50: float | None = None
    close_lag_1: float | None = None
    close_lag_5: float | None = None
    daily_return_pct: float | None = None
    absolute_return_pct: float | None = None
    rolling_volatility: float | None = None


def check_price_range(open_, high, low, close) -> None:
    """Mirror chk_high_not_below_low and keep open/close inside [low, high]."""
    if high < low:
        raise ValueError("high must be greater than or equal to low")
    for name, value in (("open", open_), ("close", close)):
        if not low <= value <= high:
            raise ValueError(f"{name} must lie between low and high")


class PriceCreate(BaseModel):
    trade_date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    indicators: Indicators = Field(default_factory=Indicators)

    @model_validator(mode="after")
    def _validate_range(self):
        check_price_range(self.open, self.high, self.low, self.close)
        return self


class PriceUpdate(BaseModel):
    """Fields to change on an existing trading day; omitted fields are kept."""

    open: float | None = Field(default=None, gt=0)
    high: float | None = Field(default=None, gt=0)
    low: float | None = Field(default=None, gt=0)
    close: float | None = Field(default=None, gt=0)
    volume: int | None = Field(default=None, ge=0)
    indicators: Indicators | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class PriceRecord(BaseModel):
    ticker: str
    company: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    indicators: Indicators


class DeleteResult(BaseModel):
    ticker: str
    trade_date: date
    deleted: bool = True
