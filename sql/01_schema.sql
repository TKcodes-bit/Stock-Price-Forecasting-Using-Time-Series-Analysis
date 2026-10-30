-- Task 2: MySQL 8.0 relational schema for AAPL time-series data
-- Dataset: Kaggle S&P 500 Stock Data (Cam Nugent), all_stocks_5yr.csv

CREATE DATABASE IF NOT EXISTS stock_timeseries
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE stock_timeseries;

CREATE TABLE IF NOT EXISTS companies (
    company_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    ticker VARCHAR(12) NOT NULL,
    company_name VARCHAR(120) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id),
    UNIQUE KEY uq_companies_ticker (ticker)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dataset_sources (
    source_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    dataset_name VARCHAR(180) NOT NULL,
    source_platform VARCHAR(60) NOT NULL,
    dataset_author VARCHAR(120) NULL,
    source_url VARCHAR(500) NOT NULL,
    source_file VARCHAR(180) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id),
    UNIQUE KEY uq_dataset_sources_name (dataset_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS daily_stock_prices (
    price_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    company_id INT UNSIGNED NOT NULL,
    source_id INT UNSIGNED NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(14,4) NOT NULL,
    high_price DECIMAL(14,4) NOT NULL,
    low_price DECIMAL(14,4) NOT NULL,
    close_price DECIMAL(14,4) NOT NULL,
    volume BIGINT UNSIGNED NOT NULL,
    inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (price_id),
    UNIQUE KEY uq_company_trade_date (company_id, trade_date),
    KEY idx_stock_prices_trade_date (trade_date),
    KEY idx_stock_prices_company_date (company_id, trade_date),
    CONSTRAINT fk_prices_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_prices_source
        FOREIGN KEY (source_id) REFERENCES dataset_sources(source_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_high_not_below_low CHECK (high_price >= low_price),
    CONSTRAINT chk_volume_nonnegative CHECK (volume >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS daily_technical_indicators (
    price_id BIGINT UNSIGNED NOT NULL,
    ma_20 DECIMAL(14,6) NULL,
    ma_50 DECIMAL(14,6) NULL,
    close_lag_1 DECIMAL(14,4) NULL,
    close_lag_5 DECIMAL(14,4) NULL,
    daily_return_pct DECIMAL(14,8) NULL,
    absolute_return_pct DECIMAL(14,8) NULL,
    rolling_volatility DECIMAL(14,8) NULL,
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (price_id),
    CONSTRAINT fk_indicators_price
        FOREIGN KEY (price_id) REFERENCES daily_stock_prices(price_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- The first rows legitimately contain NULL indicators because the selected
-- moving-average, lag, return and rolling-volatility windows need prior days.
