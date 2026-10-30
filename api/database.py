"""Connection helpers for the MySQL and MongoDB databases built in Task 2.

Settings come from the same environment variables (or .env file) used by
scripts/load_databases.py, so the API reads the data the loader wrote.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

DATASET_NAME = "S&P 500 Stock Data"
DATASET_URL = "https://www.kaggle.com/datasets/camnugent/sandp500"
DATASET_AUTHOR = "Cam Nugent"
DATASET_FILE = "all_stocks_5yr.csv"
COMPANY_NAMES = {"AAPL": "Apple Inc."}

_mysql_pool = None
_mongo_client = None


def _get_mysql_pool():
    global _mysql_pool
    if _mysql_pool is None:
        from mysql.connector import pooling

        _mysql_pool = pooling.MySQLConnectionPool(
            pool_name="stock_api",
            pool_size=int(os.getenv("MYSQL_POOL_SIZE", "5")),
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "stock_timeseries"),
        )
    return _mysql_pool


@contextmanager
def mysql_connection() -> Iterator:
    """Yield a pooled MySQL connection; roll back on error, always release."""
    connection = _get_mysql_pool().get_connection()
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def mongo_collection():
    """Return the MongoDB collection that holds one document per trading day."""
    global _mongo_client
    if _mongo_client is None:
        from pymongo import MongoClient

        _mongo_client = MongoClient(
            os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=5000,
            tz_aware=True,
        )
    database_name = os.getenv("MONGODB_DATABASE", "stock_timeseries")
    collection_name = os.getenv("MONGODB_COLLECTION", "daily_stock_prices")
    return _mongo_client[database_name][collection_name]


def close_connections() -> None:
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
