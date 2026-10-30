"""Load the AAPL slice of all_stocks_5yr.csv into MySQL and MongoDB.

The script intentionally mirrors the feature formulas in the Part 1 notebook.
It does not impute AAPL source values: the notebook reports no missing AAPL
OHLCV values or duplicate trading dates. The first windows of derived features
remain NULL until enough historical observations are available.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

# Load local .env settings automatically when python-dotenv is installed.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

DATASET_NAME = "S&P 500 Stock Data"
DATASET_URL = "https://www.kaggle.com/datasets/camnugent/sandp500"
DATASET_AUTHOR = "Cam Nugent"
DATASET_FILE = "all_stocks_5yr.csv"
TICKER = "AAPL"
COMPANY_NAME = "Apple Inc."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="Path to all_stocks_5yr.csv")
    parser.add_argument(
        "--mysql-only", action="store_true", help="Skip MongoDB loading"
    )
    parser.add_argument(
        "--mongo-only", action="store_true", help="Skip MySQL loading"
    )
    return parser.parse_args()


def _number_or_none(value: Any) -> float | int | None:
    if pd.isna(value):
        return None
    if isinstance(value, int):
        return int(value)
    return float(value)


def load_aapl_frame(csv_path: str) -> pd.DataFrame:
    path = Path(csv_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    frame = pd.read_csv(path)
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    required = {"date", "open", "high", "low", "close", "volume", "name"}
    missing_columns = required.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            "CSV is missing required columns: " + ", ".join(sorted(missing_columns))
        )

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["name"] = frame["name"].astype(str).str.strip().str.upper()
    frame = frame.loc[frame["name"].eq(TICKER)].copy()
    if frame.empty:
        raise ValueError("No AAPL rows were found in the supplied CSV.")

    frame = frame.sort_values("date").reset_index(drop=True)
    if frame["date"].isna().any():
        raise ValueError("AAPL contains invalid dates; resolve them before loading.")
    if frame["date"].duplicated().any():
        duplicates = frame.loc[frame["date"].duplicated(), "date"].astype(str).tolist()
        raise ValueError(f"Duplicate AAPL trading dates found: {duplicates[:5]}")

    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[numeric_columns].isna().any().any():
        bad = frame[numeric_columns].isna().sum()
        raise ValueError(
            "AAPL has missing/non-numeric market values. No imputation was applied; "
            f"column counts: {bad[bad > 0].to_dict()}"
        )

    # Derived variables use the same windows and formulas as Part 1.
    frame["ma_20"] = frame["close"].rolling(window=20).mean()
    frame["ma_50"] = frame["close"].rolling(window=50).mean()
    frame["close_lag_1"] = frame["close"].shift(1)
    frame["close_lag_5"] = frame["close"].shift(5)
    frame["daily_return_pct"] = frame["close"].pct_change() * 100
    frame["absolute_return_pct"] = frame["daily_return_pct"].abs()
    frame["rolling_volatility"] = frame["daily_return_pct"].rolling(window=20).std()

    return frame


def load_mysql(frame: pd.DataFrame) -> None:
    try:
        import mysql.connector
        from mysql.connector import Error
    except ImportError as exc:
        raise RuntimeError(
            "Install mysql-connector-python before loading MySQL: "
            "pip install mysql-connector-python"
        ) from exc

    required_env = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD"]
    missing_env = [key for key in required_env if key not in os.environ]
    if missing_env:
        raise RuntimeError("Missing MySQL environment variables: " + ", ".join(missing_env))

    connection = None
    try:
        connection = mysql.connector.connect(
            host=os.environ["MYSQL_HOST"],
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            database=os.getenv("MYSQL_DATABASE", "stock_timeseries"),
        )
        cursor = connection.cursor()

        cursor.execute(
            """INSERT INTO companies (ticker, company_name)
               VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE company_id = LAST_INSERT_ID(company_id),
                                       company_name = VALUES(company_name)""",
            (TICKER, COMPANY_NAME),
        )
        company_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO dataset_sources
                   (dataset_name, source_platform, dataset_author, source_url, source_file)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE source_id = LAST_INSERT_ID(source_id),
                                       source_url = VALUES(source_url),
                                       source_file = VALUES(source_file)""",
            (DATASET_NAME, "Kaggle", DATASET_AUTHOR, DATASET_URL, DATASET_FILE),
        )
        source_id = cursor.lastrowid

        # Re-load is deterministic: delete the previous AAPL history; the FK
        # on indicators cascades, then insert the current CSV slice.
        cursor.execute("DELETE FROM daily_stock_prices WHERE company_id = %s", (company_id,))

        price_rows = []
        for row in frame.itertuples(index=False):
            values = row._asdict()
            price_rows.append((
                company_id,
                source_id,
                values["date"].date(),
                float(values["open"]),
                float(values["high"]),
                float(values["low"]),
                float(values["close"]),
                int(values["volume"]),
            ))

        cursor.executemany(
            """INSERT INTO daily_stock_prices
                   (company_id, source_id, trade_date, open_price, high_price,
                    low_price, close_price, volume)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            price_rows,
        )

        cursor.execute(
            "SELECT price_id, trade_date FROM daily_stock_prices WHERE company_id = %s",
            (company_id,),
        )
        price_id_by_date = {trade_date: price_id for price_id, trade_date in cursor.fetchall()}

        indicator_rows = []
        for row in frame.itertuples(index=False):
            values = row._asdict()
            trade_date = values["date"].date()
            indicator_rows.append((
                price_id_by_date[trade_date],
                _number_or_none(values["ma_20"]),
                _number_or_none(values["ma_50"]),
                _number_or_none(values["close_lag_1"]),
                _number_or_none(values["close_lag_5"]),
                _number_or_none(values["daily_return_pct"]),
                _number_or_none(values["absolute_return_pct"]),
                _number_or_none(values["rolling_volatility"]),
            ))

        cursor.executemany(
            """INSERT INTO daily_technical_indicators
                   (price_id, ma_20, ma_50, close_lag_1, close_lag_5,
                    daily_return_pct, absolute_return_pct, rolling_volatility)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            indicator_rows,
        )
        connection.commit()
        print(f"MySQL: loaded {len(price_rows):,} AAPL prices and indicators.")
        cursor.close()
    except Error:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def load_mongodb(frame: pd.DataFrame) -> None:
    try:
        from pymongo import MongoClient, ASCENDING, DESCENDING
    except ImportError as exc:
        raise RuntimeError(
            "Install pymongo before loading MongoDB: pip install pymongo"
        ) from exc

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "stock_timeseries")
    collection_name = os.getenv("MONGODB_COLLECTION", "daily_stock_prices")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        collection = client[database_name][collection_name]
        collection.create_index(
            [("ticker", ASCENDING), ("date", DESCENDING)],
            unique=True,
            name="uq_ticker_date",
        )
        collection.create_index([("date", ASCENDING)], name="idx_trade_date")
        collection.create_index([("market.volume", DESCENDING)], name="idx_volume_desc")
        collection.delete_many({"ticker": TICKER})

        source = {
            "dataset": DATASET_NAME,
            "platform": "Kaggle",
            "author": DATASET_AUTHOR,
            "file": DATASET_FILE,
            "url": DATASET_URL,
        }
        documents = []
        for row in frame.itertuples(index=False):
            values = row._asdict()
            trade_datetime = datetime.combine(
                values["date"].date(), datetime.min.time(), tzinfo=timezone.utc
            )
            documents.append({
                "ticker": TICKER,
                "company": COMPANY_NAME,
                "date": trade_datetime,
                "market": {
                    "open": float(values["open"]),
                    "high": float(values["high"]),
                    "low": float(values["low"]),
                    "close": float(values["close"]),
                    "volume": int(values["volume"]),
                },
                "indicators": {
                    "ma_20": _number_or_none(values["ma_20"]),
                    "ma_50": _number_or_none(values["ma_50"]),
                    "close_lag_1": _number_or_none(values["close_lag_1"]),
                    "close_lag_5": _number_or_none(values["close_lag_5"]),
                    "daily_return_pct": _number_or_none(values["daily_return_pct"]),
                    "absolute_return_pct": _number_or_none(values["absolute_return_pct"]),
                    "rolling_volatility": _number_or_none(values["rolling_volatility"]),
                },
                "source": source,
            })

        if documents:
            collection.insert_many(documents, ordered=True)
        print(f"MongoDB: loaded {len(documents):,} AAPL documents.")
    finally:
        client.close()


def main() -> int:
    args = parse_args()
    if args.mysql_only and args.mongo_only:
        print("Choose at most one of --mysql-only and --mongo-only.", file=sys.stderr)
        return 2

    frame = load_aapl_frame(args.csv_path)
    print(
        f"Prepared {len(frame):,} AAPL rows from "
        f"{frame['date'].min().date()} to {frame['date'].max().date()}."
    )

    if not args.mongo_only:
        load_mysql(frame)
    if not args.mysql_only:
        load_mongodb(frame)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
