import os
import requests
import datetime
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader

# 1. 抓取全台股列表並篩選符合條件的股票
def screen_all_stocks():
    print("正在獲取台股股票清單...")
    dl = DataLoader()
    
    # 抓取台股總覽（包含上市與上櫃）
    stock_info = dl.taiwan_stock_info()
    # 僅留普通股（排除 ETF、權證、特種股）
    stock_list = stock_info[stock_info["type"].isin(["twse", "tpex"]) & (stock_info["stock_id"].str.len() == 4)]["stock_id"].tolist()
    
    # 設定抓取歷史資料區間（約需 60 天以正確計算 MA50 與 KD）
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")

    selected_stocks = []
    print(f"開始分析全市場 {len(stock_list)} 檔股票...")

    for i, stock_id in enumerate(stock_list):
        try:
            # 抓取單檔股票日 K 線
            df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
            
            if len(df) < 30:  # 資料量不足則跳過
                continue

            # 重新命名欄位以配合 pandas-ta 計算
            df = df.rename(columns={"Trading_Volume": "Volume", "close": "close", "max": "high", "min": "low"})
            
            # --- 💡 計算技術指標 ---
            # 1. 均線 (MA5, MA20)
            df["MA5"] = ta.sma(df["close"], length=5)
            df["MA20"] = ta.sma(df["close"], length=20)
            
            # 2. KD 指標 (9, 3, 3)
            kd = ta.stoch(df["high"], df["low"], df["close"], k=9, d=3)
            df["K"] = kd["STOCHk_9_3_3"]
            df["D"] = kd["STOCHd_9_3_3"]

            # 取得最新兩天資料進行條件判斷
            today = df.iloc[-1]
            yesterday = df.iloc[-2]

            # ------------------- 💡 你的選股邏輯 -------------------
            # 條件 1：均線多頭/站上均線 (收盤價 > MA5 且 MA5 > MA20)
            cond_ma = today["close"] > today["MA5"] and today["MA5"] > today["MA20"]
            
            # 條件 2：成交量暴增 (今日成交量 > 昨天成交量的 1.5 倍，且成交量 > 1000 張)
            cond_volume = (today["Volume"] > yesterday["Volume"] * 1.5) and (today["Volume"] > 1000000)
            
            # 條件 3：KD 黃金交叉或低檔黃金交叉 (昨天 K < D，今天 K > D，且 K < 80)
            cond_kd = (yesterday["K"] < yesterday["D"]) and (today["K"] > today["D"]) and (today["K"] < 80)

            # 符合全部條件即納入篩選
            if cond_ma and cond_volume and cond_kd:
                vol_shares = int(today["Volume"] / 1000)
                selected_stocks.append(f"• {stock_id} (價:{today['close']}, 量:{vol_shares}張, K:{round(today['K'],1)})")
                print(f"✅ 符合條件: {stock_id}")

        except Exception as e:
            continue

    return selected_stocks

# 2. 發送 LINE 推播
def send_line_message(message):
    token = os.environ.get("LINE_TOKEN")
    if not token:
        print("Error: 未設定 LINE_TOKEN！")
        return

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {"messages": [{"type": "text", "text": message}]}
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        print("LINE 訊息推播成功！")
    else:
        print(f"發送失敗 ({res.status_code}): {res.text}")

if __name__ == "__main__":
    results = screen_all_stocks()
    
    msg = f"📊【台股全市場選股 - 均線+量增+KD】\n符合條件標的共 {len(results)} 檔：\n\n"
    if results:
        msg += "\n".join(results[:25])  # LINE 單次訊息上限，顯示前 25 檔
    else:
        msg += "今日無符合條件標的。"
        
    send_line_message(msg)
