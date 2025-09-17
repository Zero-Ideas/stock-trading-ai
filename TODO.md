# Plan: Building a Technical Trading Bot

A step-by-step guide to developing a machine learning model for technical trading, from data processing to generating a JSON prediction output. The plan is designed to be methodical, ensuring robust evaluation and a clear final product.

---

## 🧠 Step 1: Data Preparation & Feature Engineering

### Objective
Transform raw OHLCV (Open, High, Low, Close, Volume) data into a rich feature set by calculating technical indicators. A model learns from features, not raw prices.

### Key Actions
* **Load Data**: For each of the 94 symbols, load the partitioned time-series data. It's best to work with one symbol and one timeframe (e.g., AAPL, hourly) to develop the pipeline first.
* **Calculate Indicators**: Use a library like `ta` or `pandas-ta` in Python to compute a comprehensive set of indicators.
    * **Trend Indicators**: SMA (10, 20, 50), EMA (10, 20, 50), MACD, ADX
    * **Momentum Indicators**: RSI, Stochastic Oscillator
    * **Volatility Indicators**: Bollinger Bands, ATR (Average True Range)
    * **Volume Indicators**: OBV (On-Balance Volume), VWAP (which you already have)
* **Handle Missing Data**: The initial periods for any indicator calculation will result in `NaN` values. These rows must be cleanly dropped before proceeding to the next step.

---

## 🎯 Step 2: Defining the Prediction Target (Labeling)

### Objective
Create a "target" variable for the model to predict. This turns the time-series problem into a supervised learning task.

### Recommended Approach: Classification
This approach is generally more robust than trying to predict an exact price.
* Define a future time window (e.g., `n=5` periods ahead).
* Define a price change threshold to filter out noise (e.g., `1%`).
* Create three distinct labels for your target column:
    * `1 (Buy)`: If the price **increases** by more than the threshold in `n` periods.
    * `-1 (Sell)`: If the price **decreases** by more than the threshold in `n` periods.
    * `0 (Hold)`: If the price change is within the threshold.

> **Important**: The `n` value you choose directly defines the bot's intended trading horizon (e.g., for hourly data, `n=5` means you are predicting a move over the next 5 hours).

---

## 🤖 Step 3: Model Selection & Training

### Objective
Choose an appropriate machine learning model and train it on the historical features (Step 1) and labels (Step 2).

### Model Candidates
* **Random Forest**: A great baseline model. It's robust, less prone to overfitting than a single decision tree, and provides clear feature importances.
* **XGBoost / LightGBM**: High-performance gradient boosting models. They are the standard choice for tabular data competitions and applications due to their speed and accuracy.

### Training Protocol
* **Temporal Train-Test Split**: This is the most critical rule.
    * **Train** on older data (e.g., 2016-2022).
    * **Test** on the most recent, unseen data (e.g., 2023-Present).
    * **Never** use a random split (`train_test_split` from scikit-learn without `shuffle=False`). Doing so will cause **lookahead bias** and your results will be unrealistically optimistic.
* **Model Fitting**: Train the model using `model.fit(X_train, y_train)`. It's common practice to train one specialized model per symbol.

---

## 📈 Step 4: Backtesting & Performance Analysis

### Objective
Simulate the trading strategy on the unseen test data to realistically evaluate its financial performance. **Model accuracy alone is a misleading and insufficient metric.**

### Backtesting Process
1.  Iterate through the test set, one time step at a time.
2.  At each step, feed the features into the trained model to get a `Buy`/`Sell`/`Hold` prediction.
3.  Simulate the corresponding trade in a mock portfolio, accounting for hypothetical transaction costs.
4.  Track the portfolio's value over the entire test period.

### Key Performance Metrics (KPIs)
* **Return Analysis**:
    * **Total Return (%)**: The overall profitability of the strategy.
    * **Sharpe Ratio**: Measures the risk-adjusted return. A value **> 1** is generally considered good.
* **Risk Analysis**:
    * **Max Drawdown (%)**: The largest percentage drop from a portfolio peak. This is a crucial measure of potential loss.
* **Goodness of Fit**:
    * **$R^2$ (R-squared)**: This is a regression metric. For a classification strategy, you can calculate an analogous metric by running a regression of your strategy's returns against a market benchmark (e.g., SPY). This tells you how much of your performance is independent of the overall market.

---

## 📄 Step 5: Implementation & JSON Output

### Objective
Create a final function that takes the latest market data, runs the model, and outputs a structured JSON with the prediction and pre-calculated performance analysis.

### JSON Structure
The final output should be a JSON object containing:
* The timestamp and symbol for the prediction.
* The model's string **prediction** (`Buy`, `Sell`, or `Hold`).
* A **confidence score** derived from the model's prediction probability (`model.predict_proba`).
* The pre-calculated **backtesting metrics** (Sharpe Ratio, Max Drawdown, etc.) that provide context on the strategy's viability.
* **Key drivers**: The top features that influenced the prediction (from `model.feature_importances_`).


# NOTE: THERE IS ARTIFICIAL FORWARD FILLED DATA IN THE DATABASE. THE COLUMN IS CALLED "original" and if its false it means its forward filled. There are also large chunks of forward filled data for after-market hours. Make sure the bot doesnt get confused by this. Columns should be availible in DB schema with the most important ones being open, high, low, close, volume, trade_count, vwap, and price_timestamp.

# Assemble the final JSON object
output = {
    "timestamp": pd.Timestamp.now().isoformat(),
    "symbol": symbol_name,
    "prediction": prediction_label,
    "confidence_score": float(confidence_score),
    "analysis": {
        "indicators ":{
            # should include time range, and the values used to determine the indicator
        }
        "risk_return": {
            "sharpe_ratio": backtest_metrics.get("sharpe_ratio"),
            "sortino_ratio": backtest_metrics.get("sortino_ratio"),
            "calmar_ratio": backtest_metrics.get("calmar_ratio"),
            "max_drawdown": backtest_metrics.get("max_drawdown"),
            "max_drawdown_pct": backtest_metrics.get("max_drawdown_pct")
        },
        "performance": {
            "backtest_total_return_pct": backtest_metrics.get("total_return_pct"),
            "r_squared_vs_market": backtest_metrics.get("r_squared_vs_market")
        },
        "key_drivers": feature_importances
    }
}

return json.dumps(output, indent=4)

