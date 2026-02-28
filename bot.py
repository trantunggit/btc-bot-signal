import ccxt
import pandas as pd
import requests
import os
from datetime import datetime

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        requests.get(url)

exchange = ccxt.bingx({'enableRateLimit': True})

try:
    # Lấy nến M15 (Gần nhất 100 nến)
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

    # --- TÍNH TOÁN V58 ---
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    df['vol_ma'] = df['vol'].rolling(20).mean()

    # Tín hiệu dựa trên nến vừa đóng (prev)
    prev = df.iloc[-2]
    m_mult, v_mult = 1.5, 1.4

    long = (prev['close'] > prev['open']) and ((prev['close'] - prev['open']) > (prev['atr'] * m_mult)) and (prev['vol'] > prev['vol_ma'] * v_mult)
    short = (prev['close'] < prev['open']) and ((prev['open'] - prev['close']) > (prev['atr'] * m_mult)) and (prev['vol'] > prev['vol_ma'] * v_mult)

    if long:
        send_telegram(f"🚀 [M15] MUA BTC\nGiá: {prev['close']}")
    elif short:
        send_telegram(f"🔻 [M15] BÁN BTC\nGiá: {prev['close']}")

    # --- TÍNH NĂNG THỐNG KÊ CUỐI NGÀY (Lúc 23:45) ---
    now = datetime.now()
    if now.hour == 23 and now.minute >= 45:
        # Quét lại 96 nến (tương đương 24 giờ của khung M15)
        history = df.tail(96)
        total_long = 0
        total_short = 0
        
        for i in range(len(history)):
            row = history.iloc[i]
            # Tính lại logic cho từng nến trong quá khứ
            if (row['close'] > row['open']) and ((row['close'] - row['open']) > (row['atr'] * m_mult)) and (row['vol'] > (row['vol_ma'] * v_mult)):
                total_long += 1
            if (row['close'] < row['open']) and ((row['open'] - row['close']) > (row['atr'] * m_mult)) and (row['vol'] > (row['vol_ma'] * v_mult)):
                total_short += 1
        
        summary = f"📊 TỔNG KẾT NGÀY {now.strftime('%d/%m')}\n"
        summary += f"- Tổng lệnh Long: {total_long}\n"
        summary += f"- Tổng lệnh Short: {total_short}\n"
        summary += f"- Tổng kèo: {total_long + total_short}\n"
        summary += "💡 Hãy đối chiếu với Chart V58 để xem tỉ lệ Win/Loss!"
        send_telegram(summary)

except Exception as e:
    print(f"Lỗi: {e}")
