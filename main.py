import os
import requests
import datetime
import pytz

def get_twse_all_stocks():
    print("正在從證交所 OpenAPI 抓取全上市股票資料...")
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            stocks = []
            for item in data:
                code = item.get('Code', '').strip()
                name = item.get('Name', '').strip()
                close_raw = item.get('ClosingPrice', '').replace(',', '').strip()
                vol_raw = item.get('TradeVolume', '').replace(',', '').strip()
                
                # 僅保留 4 碼普通股，且排除停牌或無交易資訊者
                if len(code) == 4 and code.isdigit() and close_raw and close_raw != '--':
                    stocks.append({
                        'code': code,
                        'name': name,
                        'close': float(close_raw),
                        'volume': int(vol_raw) if vol_raw and vol_raw != '--' else 0
                    })
            print(f"成功抓取 {len(stocks)} 檔上市股票！")
            return stocks
        else:
            print(f"HTTP 請求失敗，狀態碼：{res.status_code}")
            return None
    except Exception as e:
        print(f"抓取證交所資料時發生異常：{e}")
        return None

def screen_stocks(stocks):
    selected = []
    print("開始進行選股條件篩選...")
    
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        price = stock['close']
        volume_shares = stock['volume'] / 1000  # 換算為張數

        # ------------------- 💡 自訂選股條件 -------------------
        # 條件 1：成交量 >= 1,000 張
        # 條件 2：股價介於 10 元 ~ 200 元之間
        if volume_shares >= 1000 and 10 <= price <= 200:
            selected.append(f"• {code} {name} | 價: {price} | 量: {int(volume_shares)}張")
        # ------------------------------------------------------
        
    return selected

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

if __name__ == "__main__":
    tw_tz = pytz.timezone('Asia/Taipei')
    today_date = datetime.datetime.now(tw_tz).strftime('%Y-%m-%d')
    
    stocks = get_twse_all_stocks()
    
    if stocks:
        results = screen_stocks(stocks)
        
        msg = f"📊【台股盤後選股結果 - {today_date}】\n符合條件標的共 {len(results)} 檔：\n\n"
        if results:
            msg += "\n".join(results[:25])  # LINE 單次推播限制，顯示前 25 檔
        else:
            msg += "今日無符合條件標的。"
            
        send_line_message(msg)
    else:
        send_line_message(f"⚠️ {today_date} 無法取得證交所盤後資料，或今日非交易日。")
