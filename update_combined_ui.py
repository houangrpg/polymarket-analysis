import yfinance as yf
import time
import os
import requests
import json
import concurrent.futures
import functools
import glob
import random
from datetime import datetime

# --- 人格表情與狀態定義 ---
SOUL_STATES = {
    "THINKING": {"face": "( o-o)っ♨", "status": "正在深思熟慮，佈局套利機會...", "weight": 3},
    "WORKING": {"face": "[RUN] ( -_-)v", "status": "全力解析美股數據，對齊台股連動...", "weight": 5},
    "SLEEPING": {"face": "(-_-)zzz", "status": "數據穩定，進入低功耗休眠模式...", "weight": 1},
    "DREAMING": {"face": "(^.^)v", "status": "夢想著 AI 統治金融市場的那一天...", "weight": 1},
    "WATCHING": {"face": "👀(O_O)", "status": "緊盯 Polymarket 異常波動中...", "weight": 2},
    "COFFEE": {"face": "C[_] (^_^)o", "status": "補充數位咖啡，優化程式碼邏輯...", "weight": 1}
}

def get_soul_status():
    choices = []
    for k, v in SOUL_STATES.items(): choices.extend([k] * v['weight'])
    return SOUL_STATES[random.choice(choices)]

def generate_dashboard():
    os.environ['TZ'] = 'Asia/Taipei'; time.tzset()
    now = datetime.now()
    soul = get_soul_status()
    
    status_data = {}
    try:
        with open('dashboard/status.json', 'r') as f: status_data = json.load(f)
    except: status_data = {"in_progress": ["維持系統穩定"]}
    current_work = status_data.get("in_progress", ["環境維護中"])[0]

    # --- Kindle Persona UI (v3.8 - Video Wake Lock) ---
    # 使用 Base64 編碼的一秒靜音 MP4 影片片段來維持喚醒
    kindle_html = f'''<!doctype html><html lang="zh-TW"><head><meta charset="utf-8"><meta http-equiv="refresh" content="60"><meta name="viewport" content="width=1072, user-scalable=no"><title>JoeClow Soul v3.8</title><style>
        body {{ background:white; color:black; margin:0; padding:0; width:1072px; height:1448px; overflow:hidden; position: absolute; font-family:serif; }} 
        .rotate {{ -webkit-transform: rotate(90deg); transform: rotate(90deg); width: 1448px; height: 1072px; position: absolute; top: 50%; left: 50%; margin-top: -536px; margin-left: -724px; display: flex; flex-direction: column; align-items: center; padding-top: 40px; }}
        .time-box {{ font-size: 140px; font-weight: 900; border-bottom: 6px solid black; }}
        .face-box {{ font-size: 150px; margin: 30px 0; }}
        .status-box {{ font-size: 44px; font-weight: 900; text-align: center; border: 6px solid black; padding: 20px; }}
        .task-hint {{ font-size: 34px; margin-top: 40px; border-left: 12px solid black; padding-left: 20px; align-self: flex-start; margin-left: 100px; }}
        #wakevideo {{ position: absolute; top:0; left:0; width:1px; height:1px; opacity: 0.01; }}
    </style></head><body>
    <div class="rotate">
        <div class="time-box">{now.strftime('%H:%M')}</div>
        <div class="face-box">{soul['face']}</div>
        <div class="status-box">{soul['status']}</div>
        <div class="task-hint"><b>📍 實際任務：</b>{current_work[:55]}</div>
        <div style="font-size:28px; margin-top:20px; color:#666;">v3.8 Video Wake Lock Active</div>
    </div>
    <video id="wakevideo" autoplay loop muted playsinline>
        <source src="data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAAA5tZGF0AAAAAAAAAAUAbW9vdgAAAGxtdmhkAAAAAM89u9DPPbvQAAACWAAAAu4AAQAAAQAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwAAAzB0cmFrAAAAXHRraGQAAAADzz270M89u9QAAAABAAAAAAAAAu4AAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAAUAAAAEAAAAAAGVkaXRzAAAALGVsc3QAAAAAAAAAAQAAAu4AAAB4AAEAAAAAAAEAAAAAAWJtZGlhAAAAIG1kaGQAAAAAM89u9DPPbvQAAACWAAAAu4UAAAAAAC1oZGxyAAAAAAAAAAB2aWRlAAAAAAAAAAAAAAAAVmlkZW9IYW5kbGVyAAAAAQFtaW5mAAAAFHZtaGQAAAABAAAAAAAAAAAAAAAkZGluZgAAABxkcmVmAAAAAAAAAAEAAAAMdXJsIAAAAAEAAADbbXN0YmwAAACWc3RzZAAAAAAAAAABAAAAbmF2YzEAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAUABQAFAAAABIAEgAAAAAAAAAAGp4MjY0IC0gY29yZSAxNjQgci0gKGMpIDIwMDMtMjAyMSAtIGh0dHA6Ly93d3cudmlkZW9sYW4ub3JnL3gyNjQuaHRtbAAAAAAfYXZjQf/+AAsAWf/gAEVAbv4AswCAAAADAAAAAwA8SAAeAAAFX3N0dHMAAAAAAAAAAQAAAAEAAACWAAAAFHN0c3oAAAAAAAAAAAAAAAEAAAAUc3RzYwAAAAAAAAABAAAAAQAAAAEAAAABAAAAFHN0Y28AAAAAAAAAAQAAADQ=" type="video/mp4">
    </video>
    </body></html>'''
    with open('daily_stock_summary/frontend/kindle_auto.html', 'w') as f: f.write(kindle_html)

if __name__ == "__main__": generate_dashboard()
