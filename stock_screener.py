import pandas as pd
import yfinance as yf


def get_stock_data(symbol: str):
    """抓取單一股票的 5分K、60分K 與 日K 資料"""
    ticker = yf.Ticker(f"{symbol}.TW")

    # 取得當日 5分K (用於隔日沖)
    df_5m = ticker.history(period="1d", interval="5m")
    # 取得 60分K (用於計算 200MA)
    df_60m = ticker.history(period="60d", interval="60m")
    # 取得 日K (用於計算季線 60MA)
    df_daily = ticker.history(period="100d", interval="1d")

    return df_5m, df_60m, df_daily


def check_overnight_target(df_5m, open_price):
    """1. 隔日沖邏輯：尾盤13:00-13:30成交量放大 + 價格突破今日開盤價"""
    if df_5m.empty or open_price is None:
        return False

    df_5m = df_5m.copy()
    # 確保時間欄位格式正確
    df_5m.index = pd.to_datetime(df_5m.index)

    # 抓出 13:00 - 13:30 的資料
    late_trading = df_5m[
        df_5m.index.time >= pd.to_datetime("13:00").time()
    ]

    if late_trading.empty:
        return False

    # (a) 條件一：尾盤 5分K 平均成交量大於全天 5分K 平均成交量的 1.5 倍
    avg_volume_all = df_5m["Volume"].mean()
    avg_volume_late = late_trading["Volume"].mean()
    volume_condition = avg_volume_late > (avg_volume_all * 1.5)

    # (b) 條件二：最新收盤價突破今日開盤價
    latest_price = df_5m["Close"].iloc[-1]
    price_condition = latest_price > open_price

    return volume_condition and price_condition


def check_swing_target(df_60m, df_daily):
    """2. 波段邏輯：價格回測 60k 200均線 + 季線上揚"""
    if len(df_60m) < 200 or len(df_daily) < 60:
        return False

    df_60m = df_60m.copy()
    df_daily = df_daily.copy()

    # (a) 計算 60分K 的 200MA
    df_60m["MA200"] = df_60m["Close"].rolling(200).mean()
    latest_60m = df_60m.iloc[-1]
    ma200_val = latest_60m["MA200"]

    # 條件：當前價格落在 200MA 的 ±1% 範圍內 (代表回測支撐)
    test_ma200 = (latest_60m["Low"] <= ma200_val * 1.01) and (
        latest_60m["Close"] >= ma200_val * 0.99
    )

    # (b) 計算日K 季線 (60MA) 是否上揚 (今天的季線 > 5天前的季線)
    df_daily["MA60"] = df_daily["Close"].rolling(60).mean()
    ma60_upward = df_daily["MA60"].iloc[-1] > df_daily["MA60"].iloc[-6]

    return test_ma200 and ma60_upward
