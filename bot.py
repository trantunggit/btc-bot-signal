import ccxt
import pandas as pd
import requests
import os

# Lấy cấu hình từ GitHub Secrets
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        try:
            requests.get(url)
        except Exception as e:
            print(f"Lỗi gửi Telegram: {e}")

# --- KẾT NỐI BINGX (KHÔNG BỊ CHẶN IP) ---
exchange = ccxt.bingx({
    'enableRateLimit': True
})

try:
    # Lấy dữ liệu nến 1h từ BingX (BTC/USDT)
    # BingX trả về: [timestamp, open, high, low, close, volume]
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

    # --- TỰ TÍNH TOÁN CHỈ BÁO V58 (KHÔNG CẦN THƯ VIỆN NGOÀI) ---
    # 1. Tính ATR (14)
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()

    # 2. Tính Volume MA (20)
    df['vol_ma'] = df['vol'].rolling(20).mean()

    # --- LOGIC VÀO LỆNH V58 ---
    last = df.iloc[-1]      # Nến hiện tại (đang chạy)
    prev = df.iloc[-2]      # Nến vừa đóng (dùng nến này để tín hiệu chuẩn nhất)
    
    m_mult = 1.5
    v_mult = 1.4

    # Điều kiện MUA
    long = (prev['close'] > prev['open']) and \
           ((prev['close'] - prev['open']) > (prev['atr'] * m_mult)) and \
           (prev['vol'] > prev['vol_ma'] * v_mult)
    
    # Điều kiện BÁN
    short = (prev['close'] < prev['open']) and \
            ((prev['open'] - prev['close']) > (prev['atr'] * m_mult)) and \
            (prev['vol'] > prev['vol_ma'] * v_mult)

    if long:
        msg = f"🚀 [BingX] TÍN HIỆU MUA BTC\nGiá vào: {prev['close']}\nCheck chart V58 ngay!"
        send_telegram(msg)
        print(msg)
    elif short:
        msg = f"🔻 [BingX] TÍN HIỆU BÁN BTC\nGiá vào: {prev['close']}\nCheck chart V58 ngay!"
        send_telegram(msg)
        print(msg)
    else:
        print("BingX Bot: Đang quét... Chưa có tín hiệu thỏa mãn V58.")

except Exception as e:
    print(f"Lỗi kết nối BingX: {e}")
