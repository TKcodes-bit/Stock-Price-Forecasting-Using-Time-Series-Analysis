"""MySQL endpoints: CRUD on daily_stock_prices + daily_technical_indicators."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from mysql.connector import errorcode
from mysql.connector.errors import IntegrityError

from api.database import (
    COMPANY_NAMES,
    DATASET_AUTHOR,
    DATASET_FILE,
    DATASET_NAME,
    DATASET_URL,
    mysql_connection,
)
from api.schemas import (
    DeleteResult,
    Indicators,
    PriceCreate,
    PriceRecord,
    PriceUpdate,
    check_price_range,
)

router = APIRouter(prefix="/sql/prices", tags=["MySQL"])

INDICATOR_COLUMNS = list(Indicators.model_fields)

SELECT_RECORD = f"""
    SELECT c.ticker, c.company_name, p.price_id, p.trade_date,
           p.open_price, p.high_price, p.low_price, p.close_price, p.volume,
           {", ".join(f"i.{column}" for column in INDICATOR_COLUMNS)}
    FROM daily_stock_prices AS p
    JOIN companies AS c ON c.company_id = p.company_id
    LEFT JOIN daily_technical_indicators AS i ON i.price_id = p.price_id
    WHERE c.ticker = %s
"""

TickerQuery = Query("AAPL", min_length=1, max_length=12, description="Stock ticker")


def _to_record(row: dict) -> PriceRecord:
    def number(value):
        return None if value is None else float(value)

    return PriceRecord(
        ticker=row["ticker"],
        company=row["company_name"],
        trade_date=row["trade_date"],
        open=float(row["open_price"]),
        high=float(row["high_price"]),
        low=float(row["low_price"]),
        close=float(row["close_price"]),
        volume=int(row["volume"]),
        indicators=Indicators(**{c: number(row[c]) for c in INDICATOR_COLUMNS}),
    )


def _fetch_one(cursor, ticker: str, trade_date: date, lock: bool = False) -> dict | None:
    sql = SELECT_RECORD + " AND p.trade_date = %s"
    if lock:
        sql += " FOR UPDATE"
    cursor.execute(sql, (ticker, trade_date))
    return cursor.fetchone()


def _not_found(ticker: str, trade_date: date) -> HTTPException:
    return HTTPException(
        status.HTTP_404_NOT_FOUND, f"No {ticker} record for {trade_date.isoformat()}"
    )


def _upsert_indicators(cursor, price_id: int, indicators: dict) -> None:
    columns = ", ".join(INDICATOR_COLUMNS)
    placeholders = ", ".join(["%s"] * len(INDICATOR_COLUMNS))
    updates = ", ".join(f"{c} = VALUES({c})" for c in INDICATOR_COLUMNS)
    cursor.execute(
        f"""INSERT INTO daily_technical_indicators (price_id, {columns})
            VALUES (%s, {placeholders})
            ON DUPLICATE KEY UPDATE {updates}, calculated_at = CURRENT_TIMESTAMP""",
        (price_id, *(indicators.get(c) for c in INDICATOR_COLUMNS)),
    )


# Fixed-path routes are declared before /{trade_date} so they are matched first.


@router.get("/latest", response_model=PriceRecord, summary="Latest trading record")
def get_latest(ticker: str = TickerQuery):
    with mysql_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(SELECT_RECORD + " ORDER BY p.trade_date DESC LIMIT 1", (ticker.upper(),))
        row = cursor.fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No records for {ticker.upper()}")
    return _to_record(row)


@router.get("/range", response_model=list[PriceRecord], summary="Records by date range")
def get_range(
    start_date: date = Query(..., description="First trading date (inclusive)"),
    end_date: date = Query(..., description="Last trading date (inclusive)"),
    ticker: str = TickerQuery,
):
    if start_date > end_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start_date must not be after end_date")
    with mysql_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        # Exclusive upper bound, matching sql/02_queries.sql.
        cursor.execute(
            SELECT_RECORD
            + " AND p.trade_date >= %s AND p.trade_date < %s ORDER BY p.trade_date ASC",
            (ticker.upper(), start_date, end_date + timedelta(days=1)),
        )
        rows = cursor.fetchall()
    return [_to_record(row) for row in rows]


@router.get("", response_model=list[PriceRecord], summary="List records (newest first)")
def list_prices(
    ticker: str = TickerQuery,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    with mysql_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            SELECT_RECORD + " ORDER BY p.trade_date DESC LIMIT %s OFFSET %s",
            (ticker.upper(), limit, offset),
        )
        rows = cursor.fetchall()
    return [_to_record(row) for row in rows]


@router.post(
    "",
    response_model=PriceRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trading-day record",
)
def create_price(payload: PriceCreate, ticker: str = TickerQuery):
    ticker = ticker.upper()
    with mysql_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO companies (ticker, company_name) VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE company_id = LAST_INSERT_ID(company_id)""",
            (ticker, COMPANY_NAMES.get(ticker, ticker)),
        )
        company_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO dataset_sources
                   (dataset_name, source_platform, dataset_author, source_url, source_file)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE source_id = LAST_INSERT_ID(source_id)""",
            (DATASET_NAME, "Kaggle", DATASET_AUTHOR, DATASET_URL, DATASET_FILE),
        )
        source_id = cursor.lastrowid
        try:
            cursor.execute(
                """INSERT INTO daily_stock_prices
                       (company_id, source_id, trade_date, open_price, high_price,
                        low_price, close_price, volume)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    company_id, source_id, payload.trade_date, payload.open,
                    payload.high, payload.low, payload.close, payload.volume,
                ),
            )
        except IntegrityError as exc:
            connection.rollback()
            if exc.errno == errorcode.ER_DUP_ENTRY:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"{ticker} already has a record for {payload.trade_date.isoformat()}",
                ) from exc
            raise
        _upsert_indicators(cursor, cursor.lastrowid, payload.indicators.model_dump())
        connection.commit()
        row = _fetch_one(cursor, ticker, payload.trade_date)
    return _to_record(row)


@router.get("/{trade_date}", response_model=PriceRecord, summary="Get one trading day")
def get_price(trade_date: date, ticker: str = TickerQuery):
    ticker = ticker.upper()
    with mysql_connection() as connection:
        row = _fetch_one(connection.cursor(dictionary=True), ticker, trade_date)
    if row is None:
        raise _not_found(ticker, trade_date)
    return _to_record(row)


@router.put("/{trade_date}", response_model=PriceRecord, summary="Update a trading day")
def update_price(trade_date: date, payload: PriceUpdate, ticker: str = TickerQuery):
    ticker = ticker.upper()
    changes = payload.model_dump(exclude_unset=True)
    with mysql_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        current = _fetch_one(cursor, ticker, trade_date, lock=True)
        if current is None:
            raise _not_found(ticker, trade_date)

        merged = _to_record(current).model_dump()
        indicator_changes = changes.pop("indicators", None)
        merged.update(changes)
        try:
            check_price_range(merged["open"], merged["high"], merged["low"], merged["close"])
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

        cursor.execute(
            """UPDATE daily_stock_prices
               SET open_price = %s, high_price = %s, low_price = %s,
                   close_price = %s, volume = %s
               WHERE price_id = %s""",
            (
                merged["open"], merged["high"], merged["low"],
                merged["close"], merged["volume"], current["price_id"],
            ),
        )
        if indicator_changes is not None:
            indicators = merged["indicators"]
            indicators.update(payload.indicators.model_dump(exclude_unset=True))
            _upsert_indicators(cursor, current["price_id"], indicators)
        connection.commit()
        row = _fetch_one(cursor, ticker, trade_date)
    return _to_record(row)


@router.delete("/{trade_date}", response_model=DeleteResult, summary="Delete a trading day")
def delete_price(trade_date: date, ticker: str = TickerQuery):
    ticker = ticker.upper()
    with mysql_connection() as connection:
        cursor = connection.cursor()
        # fk_indicators_price uses ON DELETE CASCADE, so indicators go too.
        cursor.execute(
            """DELETE p FROM daily_stock_prices AS p
               JOIN companies AS c ON c.company_id = p.company_id
               WHERE c.ticker = %s AND p.trade_date = %s""",
            (ticker, trade_date),
        )
        deleted = cursor.rowcount
        connection.commit()
    if deleted == 0:
        raise _not_found(ticker, trade_date)
    return DeleteResult(ticker=ticker, trade_date=trade_date)
