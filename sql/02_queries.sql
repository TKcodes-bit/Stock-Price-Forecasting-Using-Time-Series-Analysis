-- Run after 01_schema.sql and scripts/load_databases.py.
USE stock_timeseries;

-- QUERY 1: Latest available AAPL trading observation.
SELECT c.ticker, c.company_name, p.trade_date,
       p.open_price, p.high_price, p.low_price,
       p.close_price, p.volume
FROM daily_stock_prices AS p
JOIN companies AS c ON c.company_id = p.company_id
WHERE c.ticker = 'AAPL'
ORDER BY p.trade_date DESC
LIMIT 1;

-- QUERY 2: AAPL observations from 8 to 14 February 2013 (inclusive).
-- Use an exclusive upper bound so the query is safe with DATETIME as well.
SELECT c.ticker, p.trade_date,
       p.open_price, p.high_price, p.low_price,
       p.close_price, p.volume
FROM daily_stock_prices AS p
JOIN companies AS c ON c.company_id = p.company_id
WHERE c.ticker = 'AAPL'
  AND p.trade_date >= '2013-02-08'
  AND p.trade_date <  '2013-02-15'
ORDER BY p.trade_date ASC;

-- QUERY 3: Full-period count, close-price range and average trading volume.
SELECT c.ticker,
       COUNT(*) AS observation_count,
       ROUND(AVG(p.close_price), 2) AS average_close,
       MIN(p.close_price) AS minimum_close,
       MAX(p.close_price) AS maximum_close,
       ROUND(AVG(p.volume), 2) AS average_volume
FROM daily_stock_prices AS p
JOIN companies AS c ON c.company_id = p.company_id
WHERE c.ticker = 'AAPL'
GROUP BY c.ticker;

-- Optional QUERY 4: View the engineered features for a chosen date range.
SELECT p.trade_date, p.close_price,
       i.ma_20, i.ma_50, i.close_lag_1, i.close_lag_5,
       i.daily_return_pct, i.rolling_volatility
FROM daily_stock_prices AS p
JOIN companies AS c ON c.company_id = p.company_id
LEFT JOIN daily_technical_indicators AS i ON i.price_id = p.price_id
WHERE c.ticker = 'AAPL'
  AND p.trade_date >= '2017-01-01'
  AND p.trade_date <  '2017-02-01'
ORDER BY p.trade_date;
