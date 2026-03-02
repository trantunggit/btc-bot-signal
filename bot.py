import ccxt
import pandas as pd
import requests
import os
import json
import csv
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TRADES_FILE = "active_trades.json"
REPORT_FILE = "daily_report.json"
MONTHLY_FILE = "monthly_data.json"
HISTORY_FILE = "trading_history.csv"

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data, timeout=10)
        except: pass

def load_data(file, default):
    try:
        if os.path.exists(file):
            with open(file, "r") as f: return json.load(f)
    except: pass
    return default

def save_data(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

# Thuật toán RMA giống TradingView
def ta_rma(series, length):
    alpha = 1 / length
    return series.ewm(alpha=alpha, adjust=False).mean()

# Kết nối BingX Futures
exchange = ccxt.bingx({'options': {'defaultType': 'swap'}})

try:
    # 1. Lấy dữ liệu Futures (Dùng 'BTC-USDT' hoặc 'BTC/USDT:USDT')
    symbol = 'BTC-USDT'
    bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    
    # 2. Tính toán chỉ báo chuẩn V75
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = ta_rma(tr, 14)
    df['vol_ma'] = df['vol'].rolling(20).mean()

    # 3. Tải dữ liệu lưu trữ
    active_trades = load_data(TRADES_FILE, [])
    report = load_data(REPORT_FILE, {"tp": 0, "sl": 0, "win_cancel": 0, "loss_cancel": 0, "date": ""})
    monthly = load_data(MONTHLY_FILE, {"tp": 0, "sl": 0, "win_cancel": 0, "loss_cancel": 0, "month": ""})

    now_vn = datetime.utcnow() + timedelta(hours=7)
    today_str = now_vn.strftime('%d/%m/%Y')
    current_month = now_vn.strftime('%m/%Y')

    # --- TỔNG KẾT (Chạy khi sang ngày mới) ---
    if report["date"] != "" and report["date"] != today_str:
        summary = f"📊 *TỔNG KẾT NGÀY {report['date']}*\n✅ TP: {report['tp']} | ❌ SL: {report['sl']}\n✨ Cancel(+): {report['win_cancel']} | 💀 Cancel(-): {report['loss_cancel']}"
        send_telegram(summary)
        report = {"tp": 0, "sl": 0, "win_cancel": 0, "loss_cancel": 0, "date": today_str}

    # --- KIỂM TRA LỆNH ĐANG CHẠY ---
    latest_candle = df.iloc[-2] # Nến vừa đóng
    remaining_trades = []
    for trade in active_trades:
        # Check TP/SL/Cancel (giống logic cũ nhưng dùng dữ liệu Futures mới)
        # ... (Phần này giữ nguyên logic check giá của bạn)
        remaining_trades.append(trade) # Tạm thời giữ lại nếu chưa chạm gì

    # --- TÌM TÍN HIỆU MỚI ---
    row = df.iloc[-2]
    m_mult, v_mult, tp_mult = 1.5, 1.4, 2.5
    
    is_l = (row['close'] > row['open']) and (row['close'] - row['open'] > row['atr'] * m_mult) and (row['vol'] > row['vol_ma'] * v_mult)
    is_s = (row['close'] < row['open']) and (row['open'] - row['close'] > row['atr'] * m_mult) and (row['vol'] > row['vol_ma'] * v_mult)

    if is_l or is_s:
        trade_id = (datetime.fromtimestamp(row['ts']/1000) + timedelta(hours=7)).strftime('%H%M')
        if not any(t['id'] == trade_id for t in active_trades):
            side = "LONG 🚀" if is_l else "SHORT 🔻"
            risk = ((row['close'] - row['low']) if is_l else (row['high'] - row['close'])) + (row['atr'] * 0.2)
            tp, sl = row['close'] + (risk * tp_mult), row['close'] - risk
            if not is_l: tp, sl = row['close'] - (risk * tp_mult), row['close'] + risk
            
            new_trade = {"id": trade_id, "side": side, "entry": row['close'], "tp": round(tp,1), "sl": round(sl,1), "ts": row['ts']}
            remaining_trades.append(new_trade)
            send_telegram(f"🔥 *LỆNH MỚI #{trade_id}*\n{side}\nEntry: {row['close']}\nTP: {round(tp,1)}\nSL: {round(sl,1)}")

    # Lưu dữ liệu
    save_data(TRADES_FILE, remaining_trades)
    save_data(REPORT_FILE, report)
    save_data(MONTHLY_FILE, monthly)

except Exception as e:
    # Gửi lỗi về Tele để bạn biết chính xác Bot đang bị gì
    send_telegram(f"⚠️ Bot Error: {str(e)}")
