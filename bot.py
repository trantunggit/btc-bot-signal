import ccxt
import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# 1. CẤU HÌNH
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

exchange = ccxt.bingx({'enableRateLimit': True})

try:
    # Lấy 250 nến để đảm bảo đủ dữ liệu truy vết lệnh trong 24h
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=250)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

    # --- TÍNH TOÁN CHỈ BÁO V57 ---
    df['atr'] = (pd.concat([df['high'] - df['low'], 
                     abs(df['high'] - df['close'].shift()), 
                     abs(df['low'] - df['close'].shift())], axis=1).max(axis=1)).rolling(14).mean()
    df['vol_ma'] = df['vol'].rolling(20).mean()

    m_mult, v_mult = 1.5, 1.4

    # --- TÍN HIỆU REAL-TIME (NẾN VỪA ĐÓNG) ---
    prev = df.iloc[-2]
    long_c = prev['close'] > prev['open'] and (prev['close'] - prev['open']) > (prev['atr'] * m_mult) and prev['vol'] > prev['vol_ma'] * v_mult
    short_c = prev['close'] < prev['open'] and (prev['open'] - prev['close']) > (prev['atr'] * m_mult) and prev['vol'] > prev['vol_ma'] * v_mult

    if long_c:
        risk = (prev['close'] - prev['low']) + (prev['atr'] * 0.2)
        send_telegram(f"🚀 [V57 LONG]\nGiá: {prev['close']}\n🎯 TP: {round(prev['close'] + risk*2, 1)}\n🛑 SL: {round(prev['close'] - risk, 1)}")
    elif short_c:
        risk = (prev['high'] - prev['close']) + (prev['atr'] * 0.2)
        send_telegram(f"🔻 [V57 SHORT]\nGiá: {prev['close']}\n🎯 TP: {round(prev['close'] - risk*2, 1)}\n🛑 SL: {round(prev['close'] + risk, 1)}")

    # --- THỐNG KÊ CHI TIẾT (00:15 VN) ---
    vn_now = datetime.utcnow() + timedelta(hours=7)
    if vn_now.hour == 0 and 10 <= vn_now.minute <= 25:
        # Lấy dữ liệu 24h qua (96 nến M15)
        history_start = len(df) - 97
        stats = {"tp": 0, "sl": 0, "cancel": 0, "profit": 0.0}
        
        for i in range(history_start, len(df) - 1):
            row = df.iloc[i]
            if pd.isna(row['atr']): continue
            
            is_l = row['close'] > row['open'] and (row['close'] - row['open']) > (row['atr'] * m_mult) and row['vol'] > row['vol_ma'] * v_mult
            is_s = row['close'] < row['open'] and (row['open'] - row['close']) > (row['atr'] * m_mult) and row['vol'] > row['vol_ma'] * v_mult
            
            if is_l or is_s:
                # Thiết lập SL/TP cho lệnh này
                entry = row['close']
                risk = ((entry - row['low']) if is_l else (row['high'] - entry)) + (row['atr'] * 0.2)
                target = entry + (risk * 2) if is_l else entry - (risk * 2)
                stop = entry - risk if is_l else entry + risk
                
                # Truy vết các nến tiếp theo để xem kết quả (tối đa 20 nến tiếp theo)
                outcome = "cancel"
                for j in range(i + 1, min(i + 21, len(df))):
                    next_n = df.iloc[j]
                    if is_l:
                        if next_n['high'] >= target: outcome = "tp"; break
                        if next_n['low'] <= stop: outcome = "sl"; break
                    else:
                        if next_n['low'] <= target: outcome = "tp"; break
                        if next_n['high'] >= stop: outcome = "sl"; break
                
                stats[outcome] += 1
                if outcome == "tp": stats["profit"] += 2.0 # Win được 2R
                if outcome == "sl": stats["profit"] -= 1.0 # Loss mất 1R

        total_trades = stats["tp"] + stats["sl"] + stats["cancel"]
        win_rate = (stats["tp"] / (stats["tp"] + stats["sl"]) * 100) if (stats["tp"] + stats["sl"]) > 0 else 0
        
        msg = f"📊 V57 PRO SUMMARY { (vn_now - timedelta(days=1)).strftime('%d/%m') }\n"
        msg += f"------------------------\n"
        msg += f"🎯 TP Hit: {stats['tp']}\n"
        msg += f"🛑 SL Hit: {stats['sl']}\n"
        msg += f"🚫 Cancelled: {stats['cancel']}\n"
        msg += f"------------------------\n"
        msg += f"📈 Win Rate: {round(win_rate, 1)}%\n"
        msg += f"💰 Net Profit: {round(stats['profit'], 1)}R\n"
        msg += f"💡 Lợi nhuận dựa trên tỷ lệ R:R 1:2"
        send_telegram(msg)

except Exception as e:
    print(f"Error: {e}")
