import os
import requests
import pandas as pd
import yfinance as yf

# 從環境變數讀取 LINE 金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def get_all_taiwan_stock_list():
    """動態抓取全台股（上市與上櫃）股票代碼"""
    stock_list = []
    print("正在抓取全台股股票清單...")
    
    # 1. 抓取上市股票清單
    try:
        url_twse = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        res = requests.get(url_twse)
        df_twse = pd.read_html(res.text)[0]
        df_twse.columns = df_twse.iloc[0]
        df_twse = df_twse.iloc[1:]
        
        for item in df_twse['有價證券代號及名稱'].dropna():
            parts = str(item).split()
            if len(parts) >= 2:
                code = parts[0]
                # 過濾純數字的普通股（排除 ETF、權證、特種股）
                if len(code) == 4 and code.isdigit():
                    stock_list.append(f"{code}.TW")
    except Exception as e:
        print(f"抓取上市清單失敗: {e}")

    # 2. 抓取上櫃股票清單
    try:
        url_tpex = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
        res = requests.get(url_tpex)
        df_tpex = pd.read_html(res.text)[0]
        df_tpex.columns = df_tpex.iloc[0]
        df_tpex = df_tpex.iloc[1:]
        
        for item in df_tpex['有價證券代號及名稱'].dropna():
            parts = str(item).split()
            if len(parts) >= 2:
                code = parts[0]
                if len(code) == 4 and code.isdigit():
                    stock_list.append(f"{code}.TWO")
    except Exception as e:
        print(f"抓取上櫃清單失敗: {e}")

    print(f"成功取得全台股共 {len(stock_list)} 檔股票代碼。")
    return stock_list

def check_stock_conditions(stock_id):
    """檢查單一股票條件"""
    try:
        df = yf.download(stock_id, period="2m", progress=False)
        if df.empty or len(df) < 20:
            return None
        
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        close_price = float(latest['Close'])
        ma20_price = float(latest['MA20'])
        prev_close = float(prev['Close'])
        prev_ma20 = float(prev['MA20'])
        volume_shares = float(latest['Volume']) / 1000  # 轉為張數
        
        # 條件：昨日在 20MA 下，今日向上突破，且成交量 > 1000 張
        if prev_close <= prev_ma20 and close_price > ma20_price and volume_shares > 1000:
            code = stock_id.replace('.TW', '').replace('.TWO', '')
            return f"🟢 【{code}】突破 20MA\n   收盤: {close_price:.2f} | 20MA: {ma20_price:.2f} | 成交量: {int(volume_shares)}張"
    except Exception:
        pass
    return None

def send_line_message(message):
    """透過 LINE Messaging API 發送 Push Message"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("未設定 LINE 金鑰，控制台輸出：\n", message)
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(url, headers=headers, json=payload)

def main():
    stocks = get_all_taiwan_stock_list()
    matched = []
    
    print("開始執行全台股篩選（約需 3~5 分鐘）...")
    for index, s in enumerate(stocks):
        res = check_stock_conditions(s)
        if res:
            matched.append(res)
        if (index + 1) % 200 == 0:
            print(f"已完成 {index + 1}/{len(stocks)} 檔股票掃描...")
            
    if matched:
        # LINE 一則訊息上限 2000 字，若符合條件過多則分段發送
        header = f"📊 【今日全台股突破選股結果】 (共 {len(matched)} 檔)\n\n"
        chunks = []
        current_msg = header
        
        for item in matched:
            if len(current_msg) + len(item) + 2 > 1800:
                chunks.append(current_msg)
                current_msg = item + "\n\n"
            else:
                current_msg += item + "\n\n"
        if current_msg:
            chunks.append(current_msg)
            
        for msg in chunks:
            send_line_message(msg)
    else:
        send_line_message("📊 【今日全台股突破選股結果】\n今日無符合條件的股票。")

if __name__ == "__main__":
    main()
