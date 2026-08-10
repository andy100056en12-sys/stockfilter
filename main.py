import os
import time
import requests
from stock_screener import (
    check_overnight_target,
    check_swing_target,
    get_stock_data,
)

# 從 GitHub Secrets 抓取 LINE Token
LINE_TOKEN = os.environ.get("LINE_TOKEN")

# 設定你要觀察的台股代碼清單 (可自行增減)
WATCH_LIST = ["2330", "2317", "2454", "2382", "3231", "2308"]


def send_line_message(message_text):
    """將訊息透過 LINE Broadcast API 推播出來"""
    if not LINE_TOKEN:
        print("Error: 未設定 LINE_TOKEN！")
        return

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}",
    }
    payload = {"messages": [{"type": "text", "text": message_text}]}

    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        print("LINE 訊息推播成功！")
    else:
        print(f"推播失敗 ({res.status_code}): {res.text}")


def main():
    overnight_list = []
    swing_list = []

    print("開始執行股票篩選...")

    for symbol in WATCH_LIST:
        try:
            print(f"正在分析 {symbol}...")
            df_5m, df_60m, df_daily = get_stock_data(symbol)

            if df_daily.empty:
                continue

            # 今日開盤價
            open_price = df_daily["Open"].iloc[-1]

            # 判斷隔日沖
            if check_overnight_target(df_5m, open_price):
                overnight_list.append(symbol)

            # 判斷波段
            if check_swing_target(df_60m, df_daily):
                swing_list.append(symbol)

            time.sleep(1)  # 避免頻率太快被 API 阻擋
        except Exception as e:
            print(f"處理 {symbol} 發生錯誤: {e}")

    # 組合 LINE 推播文字
    msg = "📊【今日選股策略推播】\n\n"

    msg += "⚡【1. 隔日沖標的】\n"
    if overnight_list:
        msg += "\n".join([f"• {s}" for s in overnight_list]) + "\n\n"
    else:
        msg += "無符合條件標的\n\n"

    msg += "📈【2. 波段佈局標的】\n"
    if swing_list:
        msg += "\n".join([f"• {s}" for s in swing_list])
    else:
        msg += "無符合條件標的"

    print("--- 訊息內容 ---")
    print(msg)

    # 發送通知
    send_line_message(msg)


if __name__ == "__main__":
    main()
