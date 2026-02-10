import json
import os
from datetime import datetime

# 初始化測試索引檔案
INDEX_FILE = 'raid_index.json'

def update_raid_index(project_name, url, report_file):
    history = []
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f:
            history = json.load(f)
    
    entry = {
        "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "name": project_name,
        "url": url,
        "report": report_file
    }
    history.insert(0, entry) # 最新放前面
    
    with open(INDEX_FILE, 'w') as f:
        json.dump(history[:50], f, indent=2) # 保留最近 50 次

def generate_raid_html(project_name, url, status, security_stats, performance_stats, loot_items, suggestions):
    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    report_filename = f"raid_{project_name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    
    html_content = f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>{project_name} - HIS RAID REPORT</title>
        <style>
            :root {{ --bg: #0f0c29; --card: #1b1b2f; --primary: #00d2ff; --success: #39ff14; --warning: #ffbd39; --danger: #ff3131; --text: #ffffff; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); padding: 20px; display: flex; flex-direction: column; align-items: center; }}
            .container {{ max-width: 800px; width: 100%; }}
            .quest-card {{ background: var(--card); border: 2px solid var(--primary); border-radius: 15px; padding: 20px; margin-bottom: 20px; }}
            .loot-item {{ display: inline-block; background: #333; padding: 5px 10px; border-radius: 5px; margin: 5px; font-size: 0.9em; border: 1px solid var(--primary); }}
            a {{ color: var(--primary); text-decoration: none; }}
        </style>
    </head>
    <body>
        <header style="text-align:center; margin-bottom:40px;">
            <h1>{project_name} SYSTEM RAID</h1>
            <p><a href="{url}" target="_blank">🌐 傳送門：{url}</a></p>
            <div style="background:var(--success); color:black; display:inline-block; padding:5px 15px; border-radius:20px; font-weight:bold;">{status}</div>
            <p>最後更新：{updated_at}</p>
        </header>

        <div class="quest-card">
            <h3>🛡️ 防禦等級: {security_stats['level']}</h3>
            <p>戰利品: {" ".join([f'<span class="loot-item">{x}</span>' for x in loot_items])}</p>
        </div>

        <div class="quest-card">
            <h3>📜 改善建議</h3>
            {"".join([f'<p>• {x}</p>' for x in suggestions])}
        </div>
        
        <p><a href="raid_index.html">⬅️ 返回測試紀錄列表</a></p>
    </body>
    </html>
    '''
    
    with open(report_filename, 'w') as f:
        f.write(html_content)
    
    update_raid_index(project_name, url, report_filename)
    generate_index_page()
    return report_filename

def generate_index_page():
    if not os.path.exists(INDEX_FILE): return
    with open(INDEX_FILE, 'r') as f:
        history = json.load(f)
    
    rows = "".join([f'<tr><td>{h["date"]}</td><td><b>{h["name"]}</b></td><td><a href="{h["url"]}" target="_blank">連結</a></td><td><a href="{h["report"]}" style="color:#39ff14;">[查看報告]</a></td></tr>' for h in history])
    
    index_html = f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Web-Raid 測試紀錄庫</title>
    <style>
        body {{ background:#0f0c29; color:white; font-family:sans-serif; padding:40px; text-align:center; }}
        table {{ width:100%; max-width:900px; margin:20px auto; border-collapse:collapse; background:#1b1b2f; }}
        th, td {{ padding:15px; border-bottom:1px solid #333; text-align:left; }}
        th {{ background: #00d2ff; color: black; }}
        a {{ color:#00d2ff; text-decoration:none; }}
    </style></head>
    <body>
        <h1>🗄️ Web-Raid 測試紀錄庫</h1>
        <table>
            <thead><tr><th>時間</th><th>系統名稱</th><th>目標網址</th><th>冒險報告</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        <p><a href="combined.html">🏠 返回主儀表板</a></p>
    </body>
    </html>
    '''
    with open('raid_index.html', 'w') as f:
        f.write(index_html)

if __name__ == "__main__":
    # 執行一次 HIS 的正式產出
    generate_raid_html(
        "HIS", 
        "https://his.tedpc.com.tw/hccm", 
        "MISSION ACCOMPLISHED", 
        {"level": "SS"}, 
        {"speed": "1.2s"}, 
        ["SSL已加密", "驗證碼OCR成功", "個案資料渲染正常"],
        ["強制 HTTPS 重定向", "Session 自動超時", "RWD 響應式佈局優化"]
    )
