import ccxt
import pandas as pd
import requests
import os
from datetime import datetime

# --- CẤU HÌNH ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SIGNAL_FILE = "last_signal_ts.txt"

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data)
        except Exception as e:
            print(f"Lỗi gửi Telegram: {e}")

exchange = ccxt.bingx()

try:
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    df['atr'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
    df['vol_ma'] = df['vol'].rolling(20).mean()

    m_mult, v_mult, tp_mult = 1.5, 1.4, 2.5

    last_reported_ts = 0
    if os.path.exists(SIGNAL_FILE):
        with open(SIGNAL_FILE, "r") as f:
            content = f.read().strip()
            if content: last_reported_ts = int(content)

    new_signal_ts = last_reported_ts
    msg_to_send = ""

    for i in range(len(df) - 10, len(df)):
        row = df.iloc[i]
        if pd.isna(row['atr']) or pd.isna(row['vol_ma']): continue
        
        is_l = (row['close'] > row['open']) and (row['close'] - row['open'] > row['atr'] * m_mult) and (row['vol'] > row['vol_ma'] * v_mult)
        is_s = (row['close'] < row['open']) and (row['open'] - row['close'] > row['atr'] * m_mult) and (row['vol'] > row['vol_ma'] * v_mult)
        
        if (is_l or is_s) and row['ts'] > last_reported_ts:
            side = "LONG 🚀" if is_l else "SHORT 🔻"
            risk = ((row['close'] - row['low']) if is_l else (row['high'] - row['close'])) + (row['atr'] * 0.2)
            tp = row['close'] + (risk * tp_mult) if is_l else row['close'] - (risk * tp_mult)
            sl = row['close'] - risk if is_l else row['close'] + risk
            time_str = datetime.fromtimestamp(row['ts']/1000).strftime('%H:%M %d/%m')
            
            msg_to_send = (f"🔥 *TÍN HIỆU V85 ({side})*\n\n⏰ {time_str}\n💰 Giá: {row['close']}\n🎯 TP: {round(tp, 1)}\n🛑 SL: {round(sl, 1)}")
            new_signal_ts = int(row['ts'])

    if msg_to_send != "":
        send_telegram(msg_to_send)
        with open(SIGNAL_FILE, "w") as f:
            f.write(str(new_signal_ts))
        print(f"Thành công: {new_signal_ts}")
    else:
        print("Không có tín hiệu mới.")

except Exception as e:
    print(f"Lỗi: {e}")
