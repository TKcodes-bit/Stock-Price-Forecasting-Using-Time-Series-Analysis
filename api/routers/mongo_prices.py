"""MongoDB endpoints: CRUD on the daily_stock_prices collection."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, WriteError

from api.database import (
    COMPANY_NAMES,
    DATASET_AUTHOR,
    DATASET_FILE,
    DATASET_NAME,
    DATASET_URL,
    mongo_collection,
)
from api.schemas import (
    DeleteResult,
    Indicators,
    PriceCreate,
    PriceRecord,
    PriceUpdate,
    check_price_range,
)

router = APIRouter(prefix="/mongo/prices", tags=["MongoDB"])

MARKET_FIELDS = ("open", "high", "low", "close", "volume")
DOCUMENT_VALIDATION_FAILED = 121

TickerQuery = Query("AAPL", min_length=1, max_length=12, description="Stock ticker")


def _as_datetime(trade_date: date) -> datetime:
    """Trading days are stored as midnight UTC, as in scripts/load_databases.py."""
    return datetime.combine(trade_date, time.min, tzinfo=timezone.utc)


def _to_record(document: dict) -> PriceRecord:
    market = document["market"]
    return PriceRecord(
        ticker=document["ticker"],
        company=document["company"],
        trade_date=document["date"].date(),
        **{field: market[field] for field in MARKET_FIELDS},
        indicators=Indicators(**(document.get("indicators") or {})),
    )


def _not_found(ticker: str, trade_date: date) -> HTTPException:
    return HTTPException(
        status.HTTP_404_NOT_FOUND, f"No {ticker} record for {trade_date.isoformat()}"
    )


def _raise_write_error(exc: WriteError):
    """Report $jsonSchema rejections (e.g. a ticker other than AAPL) as 422."""
    if exc.code == DOCUMENT_VALIDATION_FAILED:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Document rejected by the collection's $jsonSchema validator",
        ) from exc
    raise exc


# Fixed-path routes are declared before /{trade_date} so they are matched first.


@router.get("/latest", response_model=PriceRecord, summary="Latest trading record")
def get_latest(ticker: str = TickerQuery):
    document = mongo_collection().find_one(
        {"ticker": ticker.upper()}, sort=[("date", DESCENDING)]
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No records for {ticker.upper()}")
    return _to_record(document)


@router.get("/range", response_model=list[PriceRecord], summary="Records by date range")
def get_range(
    start_date: date = Query(..., description="First trading date (inclusive)"),
    end_date: date = Query(..., description="Last trading date (inclusive)"),
    ticker: str = TickerQuery,
):
    if start_date > end_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start_date must not be after end_date")
    cursor = mongo_collection().find(
        {
            "ticker": ticker.upper(),
            "date": {
                "$gte": _as_datetime(start_date),
                "$lt": _as_datetime(end_date + timedelta(days=1)),
            },
        }
    ).sort("date", ASCENDING)
    return [_to_record(document) for document in cursor]


@router.get("", response_model=list[PriceRecord], summary="List records (newest first)")
def list_prices(
    ticker: str = TickerQuery,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    cursor = (
        mongo_collection()
        .find({"ticker": ticker.upper()})
        .sort("date", DESCENDING)
        .skip(offset)
        .limit(limit)
    )
    return [_to_record(document) for document in cursor]


@router.post(
    "",
    response_model=PriceRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trading-day record",
)
def create_price(payload: PriceCreate, ticker: str = TickerQuery):
    ticker = ticker.upper()
    document = {
        "ticker": ticker,
        "company": COMPANY_NAMES.get(ticker, ticker),
        "date": _as_datetime(payload.trade_date),
        "market": {field: getattr(payload, field) for field in MARKET_FIELDS},
        "indicators": payload.indicators.model_dump(),
        "source": {
            "dataset": DATASET_NAME,
            "platform": "Kaggle",
            "author": DATASET_AUTHOR,
            "file": DATASET_FILE,
            "url": DATASET_URL,
        },
    }
    try:
        mongo_collection().insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{ticker} already has a record for {payload.trade_date.isoformat()}",
        ) from exc
    except WriteError as exc:
        _raise_write_error(exc)
    return _to_record(document)


@router.get("/{trade_date}", response_model=PriceRecord, summary="Get one trading day")
def get_price(trade_date: date, ticker: str = TickerQuery):
    ticker = ticker.upper()
    document = mongo_collection().find_one(
        {"ticker": ticker, "date": _as_datetime(trade_date)}
    )
    if document is None:
        raise _not_found(ticker, trade_date)
    return _to_record(document)


@router.put("/{trade_date}", response_model=PriceRecord, summary="Update a trading day")
def update_price(trade_date: date, payload: PriceUpdate, ticker: str = TickerQuery):
    ticker = ticker.upper()
    collection = mongo_collection()
    selector = {"ticker": ticker, "date": _as_datetime(trade_date)}
    current = collection.find_one(selector)
    if current is None:
        raise _not_found(ticker, trade_date)

    changes = payload.model_dump(exclude_unset=True)
    market = {**current["market"], **{k: v for k, v in changes.items() if k in MARKET_FIELDS}}
    try:
        check_price_range(market["open"], market["high"], market["low"], market["close"])
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    updates = {f"market.{k}": v for k, v in changes.items() if k in MARKET_FIELDS}
    if payload.indicators is not None:
        for name, value in payload.indicators.model_dump(exclude_unset=True).items():
            updates[f"indicators.{name}"] = value
    if not updates:
        return _to_record(current)

    try:
        document = collection.find_one_and_update(
            selector, {"$set": updates}, return_document=ReturnDocument.AFTER
        )
    except WriteError as exc:
        _raise_write_error(exc)
    if document is None:
        raise _not_found(ticker, trade_date)
    return _to_record(document)


@router.delete("/{trade_date}", response_model=DeleteResult, summary="Delete a trading day")
def delete_price(trade_date: date, ticker: str = TickerQuery):
    ticker = ticker.upper()
    result = mongo_collection().delete_one(
        {"ticker": ticker, "date": _as_datetime(trade_date)}
    )
    if result.deleted_count == 0:
        raise _not_found(ticker, trade_date)
    return DeleteResult(ticker=ticker, trade_date=trade_date)
