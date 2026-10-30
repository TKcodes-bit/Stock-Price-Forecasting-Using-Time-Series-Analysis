## Apple (AAPL) Stock Price Forecasting Using Machine Learning and Deep 
Learning

# 1. Project Overview

This project explores the use of traditional machine learning and deep 
learning techniques to forecast Apple's (AAPL) next-trading-day closing 
stock price.

The main objective is to develop and evaluate models that use historical 
stock market information to predict the following trading day's closing 
price. The project also investigates whether predicting percentage returns 
or the direction of price movement produces better results.

The experiments compare traditional regression algorithms, recurrent 
neural networks, and simple baseline forecasting methods.

# 2. Project Objectives

- Analyse historical Apple stock market data.
- Perform data cleaning and feature engineering.
- Predict the next trading day's closing price.
- Compare traditional machine learning and deep learning models.
- Investigate price-based, return-based, and direction-based forecasting.
- Evaluate models using appropriate regression and classification metrics.
- Identify the best-performing trained machine learning model and compare 
it against simple forecasting baselines.

# 3. Dataset Description

The project uses historical Apple stock market data containing **1,259 
original records and 14 columns**.

The dataset includes:

| Column | Description |
|---|---|
| `date` | Trading date |
| `open` | Opening stock price |
| `high` | Highest stock price |
| `low` | Lowest stock price |
| `close` | Closing stock price |
| `volume` | Number of shares traded |
| `Name` | Stock identifier |
| `MA_20` | 20-day moving average |
| `MA_50` | 50-day moving average |
| `close_lag_1` | Previous trading day's closing price |
| `close_lag_5` | Closing price five trading days earlier |
| `daily_return_pct` | Daily percentage price change |
| `absolute_return_pct` | Absolute daily percentage return |
| `rolling_volatility` | Rolling standard deviation of daily returns |

The dataset was sorted chronologically and checked for duplicate dates and 
missing values.

**Dataset source:** Add the original dataset provider and download link 
here.

# 4. Data Preprocessing and Feature Engineering

Several features were used to capture historical price behaviour and 
market volatility.

The following features were calculated:

- 20-day moving average.
- 50-day moving average.
- One-day closing price lag.
- Five-day closing price lag.
- Daily percentage returns.
- 20-day rolling volatility.

The prediction target was created by shifting the closing price one 
trading day forward:

```python
model_df['target_next_close'] = model_df['close'].shift(-1)
```

The final modelling dataset contained **1,209 usable observations** after 
removing rows affected by rolling-window, lag, and target-shifting 
operations.

## Prediction Target

The primary prediction task was to estimate the next trading day's closing 
price using information available after the current trading day's market 
close.

## 5. Training, Validation and Testing

The data was divided chronologically to preserve the time-series structure 
and prevent random mixing of earlier and later observations.

| Dataset | Proportion | Observations |
|---|---:|---:|
| Training | 70% | 846 |
| Validation | 15% | 181 |
| Testing | 15% | 182 |
| **Total** | **100%** | **1,209** |

The training dataset was used to fit models, while the validation dataset 
was used for model comparison and hyperparameter tuning.

The test dataset was reserved for final evaluation.

Feature scaling was fitted using training data only and then applied to 
validation data.

# 6. Machine Learning and Deep Learning Experiments

A total of ten experiments were conducted.

### Traditional Machine Learning

| Experiment | Model | MAE | RMSE | R² |
|---|---|---:|---:|---:|
| 1 | Linear Regression | 0.9405 | 1.3967 | 0.9908 |
| 2 | Random Forest | 5.9135 | 9.2443 | 0.5964 |
| 3 | Tuned Random Forest | 5.4624 | 8.5824 | 0.6522 |
| 4 | Tuned XGBoost | 6.0282 | 9.2830 | 0.5930 |
| 5 | SVR with RBF Kernel | 8.5679 | 14.3796 | 0.0235 |
| 6 | Tuned SVR | 0.9136 | 1.3737 | 0.9911 |

The tuned SVR used a pipeline containing feature standardisation and an 
RBF-kernel Support Vector Regressor. Hyperparameter tuning used 
GridSearchCV with time-series cross-validation.

### Baseline Experiment

A naive persistence baseline was introduced to determine whether the 
trained models could outperform a simple forecasting approach.

The baseline assumes that the next trading day's closing price will equal 
the current day's closing price.

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Naive Persistence | 0.8983 | 1.3550 | 0.9913 |

The baseline performed slightly better than the tuned SVR on the 
validation price-error metrics.

### Deep Learning Experiments

#### Experiment 7: Initial Deep Learning Comparison

A feedforward neural network was included in the model comparison.

The network achieved:

- Training ROC-AUC: 0.7555
- Validation ROC-AUC: 0.7218
- Training Average Precision: 0.7453
- Validation Average Precision: 0.7109

#### Experiment 8: LSTM Price Regression

An LSTM model was developed to predict the next trading day's closing 
price using the previous 20 trading days.

The architecture included:

- LSTM layer with 64 units.
- Dropout layer (20%).
- LSTM layer with 32 units.
- Dropout layer (20%).
- Dense layer with 16 units and ReLU activation.
- Output layer with one neuron.

The model used Adam optimisation, mean squared error loss, batch size 32, 
and early stopping.

**Validation R²: 0.8840**

The model captured some temporal patterns but struggled to reproduce the 
higher closing prices in the validation period.

#### Experiment 9: Return-Based LSTM

Instead of predicting absolute prices, this experiment predicted the next 
trading day's percentage return.

Predicted returns were converted back into closing-price estimates for 
evaluation.

| Metric | Result |
|---|---:|
| MAE | 0.9058 |
| RMSE | 1.3741 |
| R² | 0.9911 |
| Directional Accuracy | 50.28% |

The model did not outperform the naive persistence baseline. Its predicted 
returns also showed considerably less variation than the actual returns.

#### Experiment 10: LSTM Direction Classification

The final experiment converted next-day percentage returns into binary 
classes:

- Class 1: Positive next-day return.
- Class 0: Zero or negative next-day return.

An LSTM classification model was trained using binary cross-entropy loss 
and a sigmoid output layer.

| Metric | Result |
|---|---:|
| Accuracy | 44.20% |
| Balanced Accuracy | 50.00% |
| Precision | 0.00 |
| Recall | 0.00 |
| F1-score | 0.00 |
| ROC-AUC | 0.4921 |

The model predicted only the negative-return class on the validation set. 
It therefore failed to learn useful directional patterns and 
underperformed the majority-class baseline of 55.80%.

## 7. Best Model Selection

The Tuned Support Vector Regression (SVR) model with an RBF kernel was 
selected as the best-performing trained machine learning regression model.

Its validation performance was:

- MAE: 0.9136
- RMSE: 1.3737
- R²: 0.9911

It performed better than Linear Regression but was slightly outperformed 
by the naive persistence baseline.

Therefore, the naive persistence model remained the strongest validation 
benchmark, while Tuned SVR was the best-performing trained machine 
learning model.

Final model selection and performance claims should be confirmed using the 
previously untouched test dataset.

## 8. Evaluation Metrics

The following metrics were used throughout the experiments:

**Regression metrics**

- Mean Absolute Error (MAE): Measures the average absolute difference 
between predicted and actual values.
- Root Mean Squared Error (RMSE): Measures prediction error while 
penalising larger errors more heavily.
- R-squared (R²): Measures how much variation in the target is explained 
by the model.

**Classification metrics**

- Accuracy: Proportion of correctly classified observations.
- Precision: Proportion of positive predictions that were correct.
- Recall: Proportion of actual positive observations correctly identified.
- F1-score: Harmonic mean of precision and recall.
- Balanced Accuracy: Average recall across the classes.
- ROC-AUC: Measures the model's ability to distinguish between classes.

## 9. Key Findings

The experiments produced several important findings:

1. Linear Regression and Tuned SVR achieved strong validation regression 
results.
2. Random Forest and XGBoost did not outperform the simpler regression 
models.
3. Hyperparameter tuning substantially improved SVR performance.
4. The naive persistence baseline demonstrated that strong price-level 
accuracy does not necessarily indicate meaningful predictive ability.
5. The absolute-price LSTM struggled with higher price levels in the 
validation period.
6. The return-based LSTM produced low-variation predictions and failed to 
outperform the zero-return baseline.
7. The direction-classification LSTM failed to identify positive-return 
observations.
8. Model performance should ultimately be judged on the untouched test 
dataset, not only the validation results.

## 10. Limitations

- The dataset contains a relatively limited number of observations for 
deep learning.
- Stock prices are influenced by external factors not represented in the 
available features.
- Historical price patterns do not guarantee future market behaviour.
- The models may struggle when market conditions change.
- Strong R² values can be misleading when consecutive stock prices are 
highly correlated.
- The experiments do not establish that the models can generate profitable 
trading strategies.

## 11. Technologies Used

- Python
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Scikit-learn
- TensorFlow / Keras
- XGBoost
- Google Colab
- Joblib

## 12. Project Structure

 organisation for the project repository is:

```text
AAPL-Stock-Forecasting/
│
├── notebooks/
│   └── AAPL_Stock_Forecasting.ipynb
│
├── models/
│   └── best_tuned_svr_model.pkl
│
├── outputs/
│   ├── experiment_results.csv
│   ├── model_comparison.csv
│   └── visualisations/
│
├── README.md
└── requirements.txt
```

## 13. How to Run the Project

1. Clone the repository:

```bash
https://github.com/TKcodes-bit/Stock-Price-Forecasting-Using-Time-Series-Analysis.git
```

2. Navigate to the project directory:

```bash
cd AAPL-Stock-Forecasting
```

3. Install the required libraries:

```bash
pip install -r requirements.txt
```

4. Open the notebook in Google Colab or Jupyter Notebook.

5. Upload or connect the original dataset.

6. Run the notebook cells sequentially, beginning with data loading and 
preprocessing.

7. Review the experiment results and evaluation visualisations.

**Note:** The original dataset and any large raw data files should be 
stored separately, such as in Google Drive, rather than committed to 
GitHub.

## 14. Conclusion

This project compared traditional machine learning and deep learning 
approaches for forecasting Apple's next-trading-day closing price. Ten 
experiments explored price regression, return prediction, and direction 
classification.

Tuned SVR emerged as the best trained machine learning regression model on 
the validation dataset. However, the naive persistence baseline achieved 
slightly better validation price-error metrics. The deep learning 
experiments demonstrated that more complex architectures do not 
necessarily outperform simpler forecasting approaches.

The project highlights the importance of chronological data splitting, 
feature engineering, baseline comparisons, model evaluation, and careful 
interpretation of forecasting results.


# Task 2 — Database Design (MySQL and MongoDB)
## Database design

### MySQL

The relational design uses four tables:

1. `companies` — one row for the AAPL company identity.
2. `dataset_sources` — provenance for the Kaggle source file.
3. `daily_stock_prices` — one OHLCV row per company and trading date.
4. `daily_technical_indicators` — derived daily features linked one-to-one to a price row.

The schema has primary keys, foreign keys, a unique `(company_id, trade_date)` constraint, and date/lookup indexes. The four-table design exceeds the required minimum of three tables.

### MongoDB

The `stock_timeseries.daily_stock_prices` collection stores one document per AAPL trading day. Each document embeds `market`, `indicators`, and `source` subdocuments. A unique compound index on `{ ticker: 1, date: -1 }` prevents duplicate trading-day documents and supports latest-record/date-range queries.

### 1. Install and start the database servers

Install these applications directly on your Windows computer:

- **MySQL Server 8.0 or later**. MySQL Workbench is recommended for opening and running the `.sql` files.
- **MongoDB Community Server**. Install MongoDB Shell (`mongosh`) as well. MongoDB Compass is optional but useful for viewing the collection.
- **Python 3.10 or later**.

During MySQL setup, remember the username and password for your local database account. The usual local connection is `localhost`, port `3306`. The usual MongoDB local connection is `mongodb://localhost:27017`.

Make sure both database services are running before continuing. On Windows, open **Services** (`services.msc`) and start the MySQL and MongoDB services if they are not already running. Service names can vary by installation (for example, `MySQL80` and `MongoDB`).

You can confirm that the command-line tools are available in PowerShell with:

```powershell
mysql --version
mongosh --version
python --version
```

### 2. Download the dataset

Download `all_stocks_5yr.csv` dataset from the current repository.

### 3. Create the MySQL database and tables

**Recommended: MySQL Workbench**

1. Open MySQL Workbench and connect to your local MySQL server.
2. Select **File → Open SQL Script**.
3. Open `sql/01_schema.sql` from this folder.
4. Click the lightning-bolt **Execute** button.
5. Refresh the Schemas panel. You should see `stock_timeseries` with the four tables.

### 4. Create the MongoDB collection and indexes

Open PowerShell or Command Prompt in this folder and run:

```powershell
mongosh "mongodb://localhost:27017/stock_timeseries" --file mongodb/01_collection_setup.js
```

The script creates the `daily_stock_prices` collection, applies document validation, and creates indexes. You can inspect the collection in MongoDB Compass by connecting to `mongodb://localhost:27017` and opening the `stock_timeseries` database.

### 5. Configure the Python loader

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

### 6. Install Python dependencies

In PowerShell, from this folder, run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
pip install -r requirements.txt
```

## Execute the required queries

### MySQL

In MySQL Workbench, open `sql/02_queries.sql` and click **Execute**. Alternatively, from Command Prompt:

```cmd
mysql -u root -p stock_timeseries < sql\02_queries.sql
```

The SQL file contains three required queries: latest AAPL record, observations within a date range, and a full-period summary. An optional fourth query retrieves technical indicators for a chosen range.

### MongoDB

Run the query script from PowerShell or Command Prompt:

```powershell
mongosh "mongodb://localhost:27017/stock_timeseries" --file mongodb/02_queries.js
```

The MongoDB file runs the equivalent three required queries and an optional technical-indicator query. You can also open MongoDB Compass and inspect the returned collection documents.

## Task 3: REST API for CRUD and Time-Series Queries

A FastAPI service in `api/` exposes the Task 2 databases. Every endpoint
exists twice, under `/sql` (MySQL) and `/mongo` (MongoDB). Both return the
same JSON shape. Records are identified by `trade_date`, and an optional
`?ticker=` query parameter defaults to `AAPL`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/{db}/prices` | Create a trading-day record (with optional indicators) |
| `GET` | `/{db}/prices?limit=&offset=` | List records, newest first |
| `GET` | `/{db}/prices/{trade_date}` | Get one trading day |
| `PUT` | `/{db}/prices/{trade_date}` | Update the supplied fields of a trading day |
| `DELETE` | `/{db}/prices/{trade_date}` | Delete a trading day (MySQL cascades to indicators) |
| `GET` | `/{db}/prices/latest` | **Latest record** |
| `GET` | `/{db}/prices/range?start_date=&end_date=` | **Records by date range** (both ends inclusive) |

Run it after loading the databases with `scripts/load_databases.py`. It uses
the same `MYSQL_*` / `MONGODB_*` environment variables or `.env` file:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
# Interactive docs: http://127.0.0.1:8000/docs
curl "http://127.0.0.1:8000/sql/prices/latest"
curl "http://127.0.0.1:8000/mongo/prices/range?start_date=2013-02-08&end_date=2013-02-14"
```

Errors: `404` for an unknown date, `409` for a duplicate date on `POST`,
`422` for invalid prices (e.g. `low > high`), and `400` when
`start_date > end_date`.

## 13. How to Run the Project

1. Clone the repository:

```bash
https://github.com/TKcodes-bit/Stock-Price-Forecasting-Using-Time-Series-Analysis.git
```

2. Navigate to the project directory:

```bash
cd AAPL-Stock-Forecasting
```

3. Install the required libraries:

```bash
pip install -r requirements.txt
```

4. Open the notebook in Google Colab or Jupyter Notebook.

5. Upload or connect the original dataset.

6. Run the notebook cells sequentially, beginning with data loading and 
preprocessing.

7. Review the experiment results and evaluation visualisations.

**Note:** The original dataset and any large raw data files should be 
stored separately, such as in Google Drive, rather than committed to 
GitHub.

## 14. Conclusion

This project compared traditional machine learning and deep learning 
approaches for forecasting Apple's next-trading-day closing price. Ten 
experiments explored price regression, return prediction, and direction 
classification.

Tuned SVR emerged as the best trained machine learning regression model on 
the validation dataset. However, the naive persistence baseline achieved 
slightly better validation price-error metrics. The deep learning 
experiments demonstrated that more complex architectures do not 
necessarily outperform simpler forecasting approaches.

The project highlights the importance of chronological data splitting, 
feature engineering, baseline comparisons, model evaluation, and careful 
interpretation of forecasting results.

# Task 4: Stock Price Prediction and Forecasting
## Objective
Task 4 connects the forecasting workflow to the project's REST API. It retrieves historical AAPL records, recreates the features used by the trained model, loads the saved tuned Support Vector Regression (SVR) pipeline, and estimates the next trading record's closing price.
## Implementation
The implementation is in scripts/forecast_from_api.py. It:
1. Requests historical records from the FastAPI date-range endpoint.
2. Uses the SQL backend by default, or MongoDB when configured.
3. Sorts records by trading date and removes duplicate dates.
4. Recalculates the model input features: MA_20, MA_50, close_lag_1, close_lag_5, daily_return_pct, and rolling_volatility.
5. Removes rows that do not yet have all required feature values.
6. Loads models/best_tuned_svr_model.pkl and predicts from the latest complete feature row.
7. Prints the number of records retrieved, number of usable rows, latest market date and close, and predicted next close.
The 11 model input columns are open, high, low, close, volume, MA_20, MA_50, close_lag_1, close_lag_5, daily_return_pct, and rolling_volatility.
## Run Task 4
Run commands from the repository root. Install dependencies and activate your virtual environment first. Then start the API in one terminal:
## python -m uvicorn api.main:app --reload
The interactive API documentation is available at http://127.0.0.1:8000/docs. In a second terminal, run the forecast script:
## python scripts/forecast_from_api.py
The default configuration uses the SQL backend, AAPL, and the date range 2013-01-01 through 2018-12-31. The script also supports these optional environment variables:
| Variable | Default | Purpose |
|---|---|---|
| `API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the running API |
| `API_BACKEND` | `sql` | Select `sql` or `mongo` |
| `TICKER` | `AAPL` | Stock ticker to request |
| `START_DATE` | `2013-01-01` | First date requested |
| `END_DATE` | `2018-12-31` | Last date requested |
| `MODEL_PATH` | `models/best_tuned_svr_model.pkl` | Saved model path |


For example, to use MongoDB in a Linux/macOS terminal:
## API_BACKEND=mongo python scripts/forecast_from_api.py
On Windows PowerShell, set the variable first with $env:API_BACKEND = "mongo", then run python scripts/forecast_from_api.py.
## Output and interpretation
A successful run prints the latest available market date, its recorded closing price, and the model's predicted next trading-day close. This is the next record after the latest date returned by the API; it is not automatically a live market forecast. The included dataset covers historical dates through 2018, so the forecast may refer to the next trading day after that historical period. The output is an estimate for educational purposes, not financial advice.
## Testing status and limitations
The API application can be started and its health route and interactive documentation can be opened. However, a successful end-to-end forecast depends on a working database connection and populated historical records. In the development environment used to prepare this README, the SQL endpoint returned a MySQL authentication error for the local root account. Therefore, a successful forecast output has not been confirmed in that environment. Configure a valid database user and load the project data before treating the end-to-end workflow as tested.

The script uses the existing saved SVR pipeline; it does not retrain the model. It also does not retrieve current prices from a live stock-market provider.
## Task 4 deliverable
- scripts/forecast_from_api.py — API-based preprocessing and next-record close forecasting.
- models/best_tuned_svr_model.pkl — trained pipeline used by the script.

---

**Author:** Thomas Kweya Odongo  
**Project:** AAPL Stock Price Forecasting  
**Institution:** African Leadership University  
**Language:** Python  
**Status:** Model experimentation completed; final test-set evaluation 
