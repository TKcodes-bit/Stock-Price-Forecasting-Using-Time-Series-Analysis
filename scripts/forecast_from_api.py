"""Task 4: fetch AAPL records from the project API and forecast next close.

Run the API first, then execute from the repository root:
    python scripts/forecast_from_api.py

Optional environment variables:
    API_BASE_URL=http://127.0.0.1:8000
    API_BACKEND=sql                 # sql or mongo
    TICKER=AAPL
    MODEL_PATH=models/best_tuned_svr_model.pkl
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURE_COLUMNS = [
    "open", "high", "low", "close", "volume", "MA_20", "MA_50",
    "close_lag_1", "close_lag_5", "daily_return_pct", "rolling_volatility",
]


def fetch_records() -> list[dict]:
    """Fetch historical records from the SQL or MongoDB Task 3 endpoint."""
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    backend = os.getenv("API_BACKEND", "sql").lower()
    ticker = os.getenv("TICKER", "AAPL").upper()
    if backend not in {"sql", "mongo"}:
        raise ValueError("API_BACKEND must be either 'sql' or 'mongo'.")

    # The project dataset spans 2013–2018. Use the full available date range
    # so the 50-day moving average and lag features can be calculated reliably.
    params = urlencode({
        "start_date": os.getenv("START_DATE", "2013-01-01"),
        "end_date": os.getenv("END_DATE", "2018-12-31"),
        "ticker": ticker,
    })
    url = f"{base_url}/{backend}/prices/range?{params}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            records = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Could not reach {url}. Start the API and check its database connection."
        ) from exc

    if not isinstance(records, list) or not records:
        raise RuntimeError("The API returned no records for the requested date range.")
    return records


def preprocess(records: list[dict]) -> pd.DataFrame:
    """Re-create the feature engineering used to train the tuned SVR model."""
    rows = []
    for record in records:
        rows.append({
            "date": record["trade_date"],
            "open": record["open"],
            "high": record["high"],
            "low": record["low"],
            "close": record["close"],
            "volume": record["volume"],
        })
    data = pd.DataFrame(rows)
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date", "open", "high", "low", "close", "volume"])
    data = data.sort_values("date").drop_duplicates(subset="date", keep="last").reset_index(drop=True)

    # These formulas match the feature-engineering steps in the Task 1 notebook.
    data["MA_20"] = data["close"].rolling(window=20).mean()
    data["MA_50"] = data["close"].rolling(window=50).mean()
    data["close_lag_1"] = data["close"].shift(1)
    data["close_lag_5"] = data["close"].shift(5)
    data["daily_return_pct"] = data["close"].pct_change() * 100
    data["rolling_volatility"] = data["daily_return_pct"].rolling(window=20).std()

    # Do not impute early rolling-window rows: they are not valid model inputs.
    data = data.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
    if data.empty:
        raise RuntimeError("Not enough valid API history to build all model features.")
    return data


def main() -> int:
    model_path = Path(os.getenv("MODEL_PATH", str(ROOT / "models" / "best_tuned_svr_model.pkl")))
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model not found: {model_path}. Put best_tuned_svr_model.pkl in models/."
        )

    records = fetch_records()
    prepared = preprocess(records)
    latest = prepared.iloc[-1]
    X_latest = prepared.loc[[prepared.index[-1]], FEATURE_COLUMNS]

    # The pickle contains the fitted StandardScaler + tuned SVR pipeline.
    model = joblib.load(model_path)
    prediction = float(model.predict(X_latest)[0])

    print("\nAAPL NEXT-TRADING-DAY CLOSE FORECAST")
    print("------------------------------------")
    print(f"API records fetched : {len(records)}")
    print(f"Usable feature rows : {len(prepared)}")
    print(f"Latest market date  : {latest['date'].date().isoformat()}")
    print(f"Latest actual close : ${float(latest['close']):.2f}")
    print(f"Predicted next close: ${prediction:.2f}")
    print("Forecast horizon    : next trading-day record")
    print("Model               : tuned SVR pipeline")
    print("\nNote: this is a model estimate, not financial advice. The dataset/API may end in 2018,\nso the forecast is the next record after the latest available historical date—not today's live price.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, FileNotFoundError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
