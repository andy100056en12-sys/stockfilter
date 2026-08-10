import os
import requests
import pandas as pd

# 1. 取得全台股盤後資料（證交所 API）
def get_twse_all_stocks():
    print("正在從證交所抓取全上市股票資料...")
    # 證交所每日個股盤後資訊 API
    url = "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&type=ALLBUT0999"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print("無法取得證交所資料")
        return None

    data = res.json()
    if "data9" not in data:
        print("今日非交易日或資料尚未更新")
        return None

    # 轉為 Pandas DataFrame 方便進行選股計算
    columns = [
        "證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額",
        "開盤價", "最高價", "最低價", "收盤價", "漲跌(+/-)", "漲跌價差",
        "最後揭示買價", "最後揭示買量", "最後揭示賣價", "最後揭示賣量", "本益比"
    ]
    df = pd.DataFrame(data["data9"], columns=columns)
    
    # 清理資料型態（移除逗號、轉為數字）
    for col in ["收盤價", "成交股數", "本益比"]:
        df[col] = df[col].astype(str).str.replace(",", "").str.replace("--", "0")
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
    return df

# 2. 自訂選股邏輯（在此處撰寫你的挑選條件）
def screen_stocks(df):
    selected_stocks = []
    
    for index, row in df.iterrows():
        stock_id = row["證券代號"]
        stock_name = row["證券名稱"]
        price = row["收盤價"]
        volume = row["成交股數"] / 1000  # 換算成張數
        pe_ratio = row["本益比"]

        # ------------------- 💡 你的選股邏輯 -------------------
        # 範例條件：
        # 1. 股價 > 10 元
        # 2. 成交量 > 1,000 張
        # 3. 本益比在 0 ~ 15 之間
        if price > 10 and volume > 1000 and 0 < pe_ratio < 15:
            selected_stocks.append(f"• {stock_id} {stock_name} (股價:{price}, 量:{int(volume)}張)")
        # ------------------------------------------------------
        
    return selected_stocks

# 3. 發送 LINE 推播
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
        print("LINE 訊息發送成功！")
    else:
        print(f"發送失敗 ({res.status_code}): {res.text}")

if __name__ == "__main__":
    df = get_twse_all_stocks()
    
    if df is not None:
        results = screen_stocks(df)
        
        # 組合 LINE 訊息
        msg = f"📊【證交所台股選股結果】\n符合條件標的共 {len(results)} 檔：\n\n"
        if results:
            msg += "\n".join(results[:20])  # LINE 單次訊息長度有限，先印出前 20 檔
        else:
            msg += "今日無符合條件標的。"
            
        send_line_message(msg)
