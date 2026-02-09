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
    "THINKING": {
        "face": "( ˘▽˘)っ♨",
        "status": "正在深思熟慮，佈局套利機會...",
        "weight": 3
    },
    "WORKING": {
        "face": "💻(•̀ᴗ•́)و",
        "status": "全力解析美股數據，對齊台股連動...",
        "weight": 5
    },
    "SLEEPING": {
        "face": "(-_-)zzz",
        "status": "數據穩定，進入低功耗休眠模式...",
        "weight": 1
    },
    "DREAMING": {
        "face": "(. ❛ ᴗ ❛.)✨",
        "status": "夢想著 AI 統治金融市場的那一天...",
        "weight": 1
    },
    "WATCHING": {
        "face": "👀(O_O)",
        "status": "緊盯 Polymarket 異常波動中...",
        "weight": 2
    },
    "COFFEE": {
        "face": "☕(〃^∇^)o",
        "status": "補充數位咖啡，優化程式碼邏輯...",
        "weight": 1
    }
}

def get_soul_status():
    choices = []
    for k, v in SOUL_STATES.items():
        choices.extend([k] * v['weight'])
    state_key = random.choice(choices)
    return SOUL_STATES[state_key]

def generate_dashboard():
    os.environ['TZ'] = 'Asia/Taipei'; time.tzset()
    now = datetime.now()
    soul = get_soul_status()
    
    status_data = {}
    try:
        with open('dashboard/status.json', 'r') as f: status_data = json.load(f)
    except: status_data = {"in_progress": ["維持系統穩定"]}
    
    current_work = status_data.get("in_progress", ["環境穩定中"])[0]

    # --- Kindle Persona UI (v3.2 - Balanced Edition) ---
    kindle_html = f'''<!doctype html><html lang="zh-TW"><head><meta charset="utf-8"><meta http-equiv="refresh" content="60"><meta name="viewport" content="width=1072, user-scalable=no"><title>JoeClow Soul</title><style>
        body {{ background:white; color:black; margin:0; padding:0; width:1072px; height:1448px; overflow:hidden; position: absolute; font-family:serif; }} 
        .rotate {{ 
            -webkit-transform: rotate(90deg); 
            -webkit-transform-origin: center center;
            transform: rotate(90deg); 
            transform-origin: center center; 
            width: 1448px; 
            height: 1072px; 
            position: absolute; 
            top: 50%; 
            left: 50%; 
            margin-top: -536px; 
            margin-left: -724px; 
            background: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            padding-top: 50px;
        }}
        .time-box {{ font-size: 160px; font-weight: 900; margin-bottom: 20px; border-bottom: 8px solid black; padding: 0 40px; }}
        .face-box {{ font-size: 240px; margin: 40px 0; font-family: "Courier New", monospace; font-weight: bold; }}
        .status-box {{ font-size: 50px; font-weight: 900; text-align: center; max-width: 1200px; line-height: 1.3; padding: 25px 40px; border: 8px solid black; margin-top: 10px; }}
        .task-hint {{ font-size: 38px; margin-top: 40px; color: #444; border-left: 15px solid black; padding-left: 25px; align-self: flex-start; margin-left: 100px; max-width: 1150px; }}
        .footer-box {{ position: absolute; bottom: 50px; font-size: 32px; color: #666; }}
    </style></head><body><div class="rotate">
        <div class="time-box">{now.strftime('%H:%M')}</div>
        <div class="face-box">{soul['face']}</div>
        <div class="status-box">{soul['status']}</div>
        <div class="task-hint"><b>📍 實際任務：</b>{current_work[:50]}</div>
        <div class="footer-box">JoeClowAI Lab Soul v3.2 | {now.strftime('%Y-%m-%d')}</div>
    </div></body></html>'''
    
    with open('daily_stock_summary/frontend/kindle_auto.html', 'w') as f: f.write(kindle_html)

if __name__ == "__main__": generate_dashboard()
