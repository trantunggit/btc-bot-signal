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
MONTHLY_FILE = "monthly_data.json" # File lưu cộng dồn trong tháng
HISTORY_FILE = "trading_history.csv"

exchange = ccxt.bingx()

def send_telegram(message):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)

def load_data(file, default):
    if os.path.exists(file):
        with open(file, "r") as f: return json.load(f)
    return default

def save_data(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

try:
    # 1. Khởi tạo dữ liệu thời gian
    now_vn = datetime.utcnow() + timedelta(hours=7)
    today_str = now_vn.strftime('%d/%m/%Y')
    current_month = now_vn.strftime('%m/%Y')

    # 2. Tải dữ liệu
    report = load_data(REPORT_FILE, {"tp": 0, "sl": 0, "win_cancel": 0, "loss_cancel": 0, "date": "", "month": ""})
    monthly = load_data(MONTHLY_FILE, {"tp": 0, "sl": 0, "win_cancel": 0, "loss_cancel": 0, "month": ""})

    # --- LOGIC TỔNG KẾT THÁNG ---
    if monthly["month"] != "" and monthly["month"] != current_month:
        total = monthly["tp"] + monthly["sl"] + monthly["win_cancel"] + monthly["loss_cancel"]
        win_rate = round((monthly["tp"] + monthly["win_cancel"]) / total * 100, 2) if total > 0 else 0
        
        m_summary = (
            f"🏆 *TỔNG KẾT THÁNG {monthly['month']}*\n"
            f"━━━━━━━━━━━━━━\n"
            f"✅ Tổng TP: {monthly['tp']}\n"
            f"❌ Tổng SL: {monthly['sl']}\n"
            f"✨ Cancel Dương: {monthly['win_cancel']}\n"
            f"💀 Cancel Âm: {monthly['loss_cancel']}\n"
            f"📊 Winrate: {win_rate}%\n"
            f"📝 Tổng lệnh: {total}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📂 Chi tiết xem tại file: `trading_history.csv`"
        )
        send_telegram(m_summary)
        # Reset dữ liệu tháng mới
        monthly = {"tp": 0, "sl": 0, "win_cancel": 0, "loss_cancel": 0, "month": current_month}

    # --- LOGIC TỔNG KẾT NGÀY ---
    if report["date"] != "" and report["date"] != today_str:
        summary = f"📊 *TỔNG KẾT NGÀY {report['date']}*\n\n✅ TP: {report['tp']}\n❌ SL: {report['sl']}\n✨ Cancel (+): {report['win_cancel']}\n💀 Cancel (-): {report['loss_cancel']}"
        send_telegram(summary)
        report = {"tp": 0, "sl": 0, "win_cancel": 0, "loss_cancel": 0, "date": today_str, "month": current_month}

    # 3. Phần theo dõi lệnh (Khi một lệnh đóng, cộng vào cả Report và Monthly)
    # Ví dụ khi chạm TP:
    # report["tp"] += 1
    # monthly["tp"] += 1
    # log_to_csv(...) 

    # (Đoạn này bạn copy logic check lệnh từ bản V87 của tôi, 
    # chỉ cần nhớ mỗi khi cộng vào report thì cộng luôn vào monthly)

    # 4. Lưu lại
    save_data(REPORT_FILE, report)
    save_data(MONTHLY_FILE, monthly)

except Exception as e:
    print(f"Lỗi: {e}")
