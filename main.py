import os
import requests
import datetime
import pytz
import pandas as pd
import pandas_ta as ta

# 1. 抓取證交所全上市股票當日盤後資料
def get_twse_all_stocks():
    tw_tz = pytz.timezone('Asia/Taipei')
    today_str = datetime.datetime.now(tw_tz).strftime('%Y%m%d')
    print(f"正在抓取證交所全上市股票資料（日期：{today_str}）...")
    
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today_str}&type=ALLBUT0999"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"HTTP 請求失敗，狀態碼：{res.status_code}")
            return None
            
        data = res.json()
        print("API 回傳訊息：", data.get('stat'))

        # 證交所 API 回傳 'OK' 且包含 data9 表格才算成功取得
        if data.get('stat') == 'OK' and 'data9' in data:
            columns = [
                "證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額",
                "開盤價", "最高價", "最低價", "收盤價", "漲跌(+/-)", "漲跌價差",
                "最後揭示買價", "最後揭示買量", "最後揭示賣價", "最後揭示賣量", "本益比"
            ]
            df = pd.DataFrame(data["data9"], columns=columns)
            
            # 清理數值欄位（處理逗號與無數值問題）
            for col in ["收盤價", "最高價", "最低價", "開盤價", "成交股數", "本益比"]:
                df[col] = df[col].astype(str).str.replace(",", "").str.replace("--", "0")
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                
            # 僅保留一般 4 碼股票代號
            df = df[df["證券代號"].str.len() == 4].reset_index(drop=True)
            return df
        else:
            print("無法抓取個股資料，可能非交易日或資料尚未上架。")
            return None

    except Exception as e:
        print("抓取證交所資料時發生異常：", e)
        return None

# 2. 自訂選股邏輯 (均線 + 量增 + 本益比)
def screen_stocks(df):
    selected_stocks = []
    print("開始進行選股條件篩選...")
    
    for index, row in df.iterrows():
        stock_id = row["證券代號"]
        stock_name = row["證券名稱"]
        price = row["收盤價"]
        volume_shares = row["成交股數"] / 1000  # 換算為張數
        pe = row["本益比"]

        # ------------------- 💡 你的選股條件設定 -------------------
        # 條件 1：成交量 > 1,000 張
        # 條件 2：股價介於 10 元 ~ 200 元之間
        # 條件 3：本益比小於 20 且大於 0
        if volume_shares >= 1000 and 10 <= price <= 200 and 0 < pe <= 20:
            selected_stocks.append(
                f"• {stock_id} {stock_name} | 價: {price} | 量: {int(volume_shares)}張 | PER: {pe}"
            )
        # --------------------------------------------------------

    return selected_stocks

# 3. 發送 LINE 推播訊息
def send_line_message(message):
    token = os.environ.get("LINE_TOKEN")
    if not token:
        print("Error: 未設定 LINE_TOKEN 環境變數！")
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
        print(f"LINE 推播失敗 ({res.status_code}): {res.text}")

# 4. 主流程
if __name__ == "__main__":
    df = get_twse_all_stocks()
    
    if df is not None:
        results = screen_stocks(df)
        
        tw_tz = pytz.timezone('Asia/Taipei')
        today_date = datetime.datetime.now(tw_tz).strftime('%Y-%m-%d')
        
        msg = f"📊【台股全市場選股結果 - {today_date}】\n符合條件標的共 {len(results)} 檔：\n\n"
        
        if results:
            # LINE 單次訊息長度有限，先印出前 20 檔
            msg += "\n".join(results[:20])
        else:
            msg += "今日無符合條件標的。"
            
        send_line_message(msg)
    else:
        # 當日非交易日或資料未更新時，發送 LINE 提醒
        send_line_message("⚠️ 今日無盤後交易資料，或證交所資料尚未更新（請於交易日 15:30 後執行）。")
