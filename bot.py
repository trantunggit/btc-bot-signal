import ccxt
import pandas as pd
import requests
import os
import json
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Kết nối BingX với cấu hình lấy dữ liệu phái sinh (Swap)
exchange = ccxt.bingx({
    'options': {
        'defaultType': 'swap', # Ép buộc lấy dữ liệu Futures/Perpetual
    }
})

def ta_rma(series, length):
    alpha = 1 / length
    return series.ewm(alpha=alpha, adjust=False).mean()

def calculate_atr(df, length=14):
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return ta_rma(tr, length)

try:
    # Lấy dữ liệu BTC-USDT (Mã cho Perpetual Futures trên BingX)
    symbol = 'BTC-USDT' 
    bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    
    # Tính toán chỉ báo (Đồng bộ RMA với TradingView)
    df['atr'] = calculate_atr(df, 14)
    df['vol_ma'] = df['vol'].rolling(20).mean()

    # (Các phần logic quản lý lệnh, TP/SL, và gửi Telegram giữ nguyên như bản V89)
    # ...
    
    print(f"Đã cập nhật dữ liệu từ {symbol} (Futures)")

except Exception as e:
    print(f"Lỗi khi lấy dữ liệu Futures: {e}")
