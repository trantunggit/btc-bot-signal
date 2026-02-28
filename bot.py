import ccxt
import pandas as pd
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

# Kết nối Binance
exchange = ccxt.binance()
bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=100)
df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

# --- TỰ TÍNH TOÁN CHỈ BÁO (KHÔNG CẦN PANDAS-TA) ---
# 1. Tính ATR (Average True Range)
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = ranges.max(axis=1)
df['atr'] = true_range.rolling(14).mean()

# 2. Tính Volume MA
df['vol_ma'] = df['vol'].rolling(20).mean()

# --- LOGIC V58 ---
last = df.iloc[-1]
m_mult = 1.5
v_mult = 1.4

long = (last['close'] > last['open']) and ((last['close'] - last['open']) > (last['atr'] * m_mult)) and (last['vol'] > last['vol_ma'] * v_mult)
short = (last['close'] < last['open']) and ((last['open'] - last['close']) > (last['atr'] * m_mult)) and (last['vol'] > last['vol_ma'] * v_mult)

if long:
    send_telegram(f"🚀 MUA BTC (V58)\nGiá: {last['close']}\nCheck chart ngay!")
elif short:
    send_telegram(f"🔻 BÁN BTC (V58)\nGiá: {last['close']}\nCheck chart ngay!")
else:
    print("Đang quét tín hiệu... Hiện chưa có kèo.")
