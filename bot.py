import ccxt
import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# 1. CẤU HÌNH HỆ THỐNG
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        try:
            requests.post(url, data=data)
        except Exception as e:
            print(f"Lỗi gửi Telegram: {e}")

# 2. KHỞI TẠO SÀN BINGX
exchange = ccxt.bingx({'enableRateLimit': True})

try:
    # Lấy 100 nến M15
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

    # --- TÍNH TOÁN CHỈ BÁO V57 ---
    atr = (pd.concat([df['high'] - df['low'], 
                     abs(df['high'] - df['close'].shift()), 
                     abs(df['low'] - df['close'].shift())], axis=1).max(axis=1)).rolling(14).mean()
    vol_ma = df['vol'].rolling(20).mean()

    # Thêm vào dataframe để tính toán lịch sử
    df['atr'] = atr
    df['vol_ma'] = vol_ma

    # --- LOGIC VÀO LỆNH V57 ---
    momentum_mult = 1.5
    vol_mult = 1.4

    # Xét nến vừa đóng (prev)
    prev = df.iloc[-2]
    
    long_cond = prev['close'] > prev['open'] and (prev['close'] - prev['open']) > (prev['atr'] * momentum_mult) and prev['vol'] > prev['vol_ma'] * vol_mult
    short_cond = prev['close'] < prev['open'] and (prev['open'] - prev['close']) > (prev['atr'] * momentum_mult) and prev['vol'] > prev['vol_ma'] * vol_mult

    if long_cond:
        # Tính SL/TP theo đúng V57 (RR 1:2)
        risk = (prev['close'] - prev['low']) + (prev['atr'] * 0.2)
        tp = prev['close'] + (risk * 2)
        sl = prev['close'] - risk
        send_telegram(f"🚀 [V57 - LONG] BTC\nGiá vào: {prev['close']}\n🎯 TP: {round(tp, 2)}\n🛑 SL: {round(sl, 2)}")
    
    elif short_cond:
        risk = (prev['high'] - prev['close']) + (prev['atr'] * 0.2)
        tp = prev['close'] - (risk * 2)
        sl = prev['close'] + risk
        send_telegram(f"🔻 [V57 - SHORT] BTC\nGiá vào: {prev['close']}\n🎯 TP: {round(tp, 2)}\n🛑 SL: {round(sl, 2)}")

    # --- TỔNG KẾT 00:15 VIỆT NAM ---
    vn_now = datetime.utcnow() + timedelta(hours=7)
    
    # Kiểm tra khung giờ 00:10 - 00:25 sáng
    if vn_now.hour == 0 and 10 <= vn_now.minute <= 25:
        history = df.tail(96) # 24 tiếng M15
        total_long = 0
        total_short = 0
        
        for i in range(len(history)):
            r = history.iloc[i]
            if pd.isna(r['atr']): continue
            
            is_l = r['close'] > r['open'] and (r['close'] - r['open']) > (r['atr'] * momentum_mult) and r['vol'] > r['vol_ma'] * vol_mult
            is_s = r['close'] < r['open'] and (r['open'] - r['close']) > (r['atr'] * momentum_mult) and r['vol'] > r['vol_ma'] * vol_mult
            
            if is_l: total_long += 1
            if is_s: total_short += 1
            
        date_str = (vn_now - timedelta(days=1)).strftime('%d/%m/%Y')
        msg = f"📊 V57 SUMMARY {date_str}\n"
        msg += f"------------------------\n"
        msg += f"✅ Long Signals: {total_long}\n"
        msg += f"❌ Short Signals: {total_short}\n"
        msg += f"🔥 Total: {total_long + total_short}\n"
        msg += f"------------------------\n"
        msg += f"💡 RR 1:2 - Target +5%/Day"
        send_telegram(msg)

except Exception as e:
    print(f"Error: {e}")
