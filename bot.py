import ccxt
import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# 1. CẤU HÌNH HỆ THỐNG (Lấy từ GitHub Secrets)
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}"
        data = {"chat_id": CHAT_ID, "text": message}
        try:
            requests.post(url, data=data)
        except Exception as e:
            print(f"Lỗi gửi Telegram: {e}")

# 2. KHỞI TẠO SÀN BINGX
exchange = ccxt.bingx({
    'enableRateLimit': True
})

try:
    # Lấy dữ liệu 100 nến M15 gần nhất
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

    # --- TÍNH TOÁN CHỈ BÁO V58 ---
    # Tính ATR (14) thủ công
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()

    # Tính Volume MA (20)
    df['vol_ma'] = df['vol'].rolling(20).mean()

    # --- KIỂM TRA TÍN HIỆU NẾN VỪA ĐÓNG (PREV) ---
    prev = df.iloc[-2]
    m_mult = 1.5  # Hệ số Momentum
    v_mult = 1.4  # Hệ số Volume

    # Điều kiện MUA (Long)
    long_signal = (prev['close'] > prev['open']) and \
                  ((prev['close'] - prev['open']) > (prev['atr'] * m_mult)) and \
                  (prev['vol'] > prev['vol_ma'] * v_mult)
    
    # Điều kiện BÁN (Short)
    short_signal = (prev['close'] < prev['open']) and \
                   ((prev['open'] - prev['close']) > (prev['atr'] * m_mult)) and \
                   (prev['vol'] > prev['vol_ma'] * v_mult)

    # Gửi tin nhắn nếu có kèo mới
    if long_signal:
        send_telegram(f"🚀 [M15 - BingX] TÍN HIỆU MUA BTC\nGiá vào: {prev['close']}\nCheck chart V58 ngay!")
    elif short_signal:
        send_telegram(f"🔻 [M15 - BingX] TÍN HIỆU BÁN BTC\nGiá vào: {prev['close']}\nCheck chart V58 ngay!")
    else:
        print(f"[{datetime.now()}] Bot đang quét... Chưa có tín hiệu.")

    # --- LOGIC TỔNG KẾT CUỐI NGÀY (Lúc 00:15 Việt Nam) ---
    # Giờ VN = Giờ UTC + 7
    vn_now = datetime.utcnow() + timedelta(hours=7)
    
    # Nếu giờ là 00 (12h đêm) và phút từ 10 đến 25 (để khớp lịch chạy 15p/lần)
    if vn_now.hour == 0 and 10 <= vn_now.minute <= 25:
        history = df.tail(96) # 96 nến 15p = 24h
        total_long = 0
        total_short = 0
        
        for i in range(len(history)):
            row = history.iloc[i]
            # Tính lại logic check cho từng nến lịch sử
            is_long = (row['close'] > row['open']) and \
                      ((row['close'] - row['open']) > (row['atr'] * m_mult)) and \
                      (row['vol'] > (row['vol_ma'] * v_mult))
            
            is_short = (row['close'] < row['open']) and \
                       ((row['open'] - row['close']) > (row['atr'] * m_mult)) and \
                       (row['vol'] > (row['vol_ma'] * v_mult))
            
            if is_long: total_long += 1
            if is_short: total_short += 1
            
        date_str = (vn_now - timedelta(days=1)).strftime('%d/%m/%Y')
        summary = f"📊 TỔNG KẾT NGÀY {date_str}\n"
        summary += f"------------------------\n"
        summary += f"✅ Tổng lệnh Long: {total_long}\n"
        summary += f"❌ Tổng lệnh Short: {total_short}\n"
        summary += f"🔥 Tổng kèo V58: {total_long + total_short}\n"
        summary += f"------------------------\n"
        summary += f"💡 Mục tiêu: +5% mỗi ngày!"
        
        send_telegram(summary)
        print("Đã gửi báo cáo tổng kết.")

except Exception as e:
    print(f"Lỗi vận hành: {e}")
