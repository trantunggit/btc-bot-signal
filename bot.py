name: BTC V85 Bot Runner

on:
  schedule:
    - cron: '*/15 * * * *' # Chạy mỗi 15 phút
  workflow_dispatch:      # Cho phép bạn nhấn nút chạy tay để test

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install ccxt pandas requests

      - name: Run Bot V85
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python bot.py

      - name: Commit and Push if Signal Updated
        run: |
          git config --global user.name "GitHub Action Bot"
          git config --global user.email "actions@github.com"
          git add last_signal_ts.txt || true
          git commit -m "Update last signal timestamp [skip ci]" || true
          git push
