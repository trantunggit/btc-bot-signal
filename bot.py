import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

exchange = ccxt.binance()
# Lấy nến 1h (Timeframe 1h)
bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=100)
df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
df['vol_ma'] = ta.sma(df['volume'], length=20)

last = df.iloc[-1]
momentum_mult = 1.5
vol_mult = 1.4

long_cond = (last['close'] > last['open']) and ((last['close'] - last['open']) > (last['atr'] * momentum_mult)) and (last['volume'] > last['vol_ma'] * vol_mult)
short_cond = (last['close'] < last['open']) and ((last['open'] - last['close']) > (last['atr'] * momentum_mult)) and (last['volume'] > last['vol_ma'] * vol_mult)

if long_cond:
    send_telegram(f"🚀 MUA BTC\nGiá: {last['close']}\n(Check Chart V58 ngay!)")
elif short_cond:
    send_telegram(f"🔻 BÁN BTC\nGiá: {last['close']}\n(Check Chart V58 ngay!)")
else:
    print("Chưa có tín hiệu mới.")
