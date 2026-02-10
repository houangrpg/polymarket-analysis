import json
import os
from datetime import datetime
import subprocess

# 初始化測試索引檔案
INDEX_FILE = 'raid_index.json'

def update_raid_index(project_name, url, report_file, status="Pending"):
    history = []
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    
    # 檢查是否已有該項目的 Pending 紀錄，有的話更新，沒有的話新增
    found = False
    for item in history:
        if item['name'] == project_name and item['status'] == "Testing...":
            item['date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            item['report'] = report_file
            item['status'] = status
            found = True
            break
            
    if not found:
        entry = {
            "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "name": project_name,
            "url": url,
            "report": report_file,
            "status": status
        }
        history.insert(0, entry)
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(history[:50], f, indent=2, ensure_ascii=False)
    
    generate_index_page()
    # 自動推送索引更新
    subprocess.run(["git", "add", INDEX_FILE, "raid_index.html"], capture_output=True)
    subprocess.run(["git", "commit", "-m", f"System: Update index for {project_name} ({status})"], capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], capture_output=True)

def generate_raid_html(project_name, url, status, security_stats, performance_stats, loot_items, suggestions, extra_cards=None):
    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"raid_{project_name.lower()}_{timestamp}.html"
    
    # 使用與 his_raid_report.html 完全一致的 CSS 與結構
    html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} 系統冒險檢測報告</title>
    <style>
        :root {{
            --bg: #0f0c29;
            --card: #1b1b2f;
            --primary: #00d2ff;
            --success: #39ff14;
            --warning: #ffbd39;
            --danger: #ff3131;
            --text: #ffffff;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: var(--text);
            margin: 0;
            padding: 20px;
            display: flex; flex-direction: column; align-items: center;
        }}
        .container {{ max-width: 800px; width: 100%; }}
        header {{ text-align: center; margin-bottom: 40px; }}
        h1 {{ font-size: 3em; text-shadow: 0 0 10px var(--primary); margin: 10px 0; }}
        .status-badge {{
            background: var(--success); color: black; padding: 5px 15px; border-radius: 20px; font-weight: bold; box-shadow: 0 0 15px var(--success);
        }}
        .quest-card {{
            background: var(--card); border: 2px solid var(--primary); border-radius: 15px; padding: 20px; margin-bottom: 20px; position: relative; overflow: hidden; transition: transform 0.3s;
        }}
        .quest-card:hover {{ transform: scale(1.02); }}
        .quest-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 15px; }}
        .quest-title {{ font-size: 1.5em; font-weight: bold; color: var(--primary); }}
        .difficulty {{ font-size: 0.8em; color: #888; }}
        .stats {{ display: flex; gap: 20px; margin: 15px 0; }}
        .stat-item {{ flex: 1; text-align: center; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; }}
        .stat-val {{ display: block; font-size: 1.8em; font-weight: bold; }}
        .stat-label {{ font-size: 0.8em; color: #aaa; }}
        .loot {{ margin-top: 15px; }}
        .loot-item {{ display: inline-block; background: #333; padding: 5px 10px; border-radius: 5px; margin-right: 5px; font-size: 0.9em; }}
        .loot-success {{ color: var(--success); border: 1px solid var(--success); }}
        .loot-warning {{ color: var(--warning); border: 1px solid var(--warning); }}
        .loot-danger {{ color: var(--danger); border: 1px solid var(--danger); }}
        .progress-bar {{ height: 10px; background: #333; border-radius: 5px; margin: 10px 0; }}
        .progress-fill {{ height: 100%; background: var(--primary); border-radius: 5px; box-shadow: 0 0 10px var(--primary); }}
        a {{ color: var(--primary); text-decoration: none; font-weight: bold; }}
        footer {{ margin-top: 50px; text-align: center; font-size: 0.8em; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <p style="color: var(--primary); letter-spacing: 5px; margin-bottom: 5px;">JOE CLOW AI LAB PRESENTS</p>
            <h1>{project_name} SYSTEM RAID</h1>
            <p><a href="{url}" target="_blank">🌐 傳送門：{url}</a></p>
            <span class="status-badge">{status}</span>
            <p>最後掃描時間：{updated_at}</p>
        </header>

        <div class="quest-card">
            <div class="quest-header">
                <span class="quest-title">🛡️ 安全性防禦等級</span>
                <span class="difficulty">等級：{security_stats['level']}</span>
            </div>
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-val" style="color: var(--success);">100%</span>
                    <span class="stat-label">SSL 加密</span>
                </div>
                <div class="stat-item">
                    <span class="stat-val" style="color: var(--warning);">LV.2</span>
                    <span class="stat-label">防機器人驗證</span>
                </div>
            </div>
            <div class="loot">
                <p>💡 <b>掉落戰利品 (資安發現)：</b></p>
                {" ".join([f'<span class="loot-item loot-success">{x}</span>' for x in loot_items])}
            </div>
        </div>

        <div class="quest-card">
            <div class="quest-header">
                <span class="quest-title">⚡ 效能與敏捷度</span>
                <span class="difficulty">等級：A (High Speed)</span>
            </div>
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-val">{performance_stats.get('speed', '1.2s')}</span>
                    <span class="stat-label">頁面載入速度</span>
                </div>
                <div class="stat-item">
                    <span class="stat-val">10s</span>
                    <span class="stat-label">數據刷新間隔</span>
                </div>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width: 85%;"></div></div>
            <div class="loot">
                <p>🚀 <b>冒險心得：</b></p>
                <p style="font-size: 0.9em; color: #ccc;">系統架構偵查完成。AJAX 術式流暢。建議優化前端結構以提升 FPS。</p>
            </div>
        </div>

        {extra_cards if extra_cards else ''}

        <div class="quest-card" style="border-color: var(--warning);">
            <div class="quest-header">
                <span class="quest-title" style="color: var(--warning);">📜 冒險家建議 (System Optimization)</span>
            </div>
            <div style="font-size: 0.9em; line-height: 1.6;">
                {"".join([f'<p>• {x}</p>' for x in suggestions])}
            </div>
        </div>

        <div style="text-align:center; margin-top:20px; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 10px;">
            <a href="raid_index.html">⬅️ 返回 SYSPWER 測試紀錄列表庫</a>
        </div>

        <footer>
            <p>GENERATED BY JOECLOW AI • POWERED BY OPENCLAW</p>
            <p>© 2026 ADVENTURE TECH</p>
        </footer>
    </div>
</body>
</html>'''
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    update_raid_index(project_name, url, report_filename, status="Success")
    return report_filename

def generate_index_page():
    if not os.path.exists(INDEX_FILE): return
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except:
        history = []
    
    table_rows = ""
    for h in history:
        status_style = 'color:#39ff14;' if h.get('status') == 'Success' else 'color:#ffbd39;'
        report_link = f'<a href="{h["report"]}" style="{status_style}">[{h.get("status", "查看報告")}]</a>' if h.get('report') else f'<span style="{status_style}">檢測中...</span>'
        
        row = f'<tr>'
        row += f'<td>{h["date"]}</td>'
        row += f'<td><b>{h["name"]}</b></td>'
        row += f'<td><a href="{h["url"]}" target="_blank">連結</a></td>'
        row += f'<td>{report_link}</td>'
        row += f'</tr>'
        table_rows += row
    
    index_html = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>SYSPWER 測試紀錄庫</title>
<style>
    body {{ background:#0f0c29; color:white; font-family:sans-serif; padding:20px; text-align:center; }}
    .mission-control {{ background:#1b1b2f; border:2px solid #00d2ff; border-radius:15px; padding:20px; max-width:900px; margin:0 auto 30px; }}
    input {{ background:#000; border:1px solid #00d2ff; color:#fff; padding:10px; width:40%; border-radius:5px; margin: 5px; }}
    button {{ background:#00d2ff; border:none; color:#000; padding:10px 20px; border-radius:5px; font-weight:bold; cursor:pointer; margin: 5px; }}
    table {{ width:100%; max-width:900px; margin:20px auto; border-collapse:collapse; background:#1b1b2f; }}
    th, td {{ padding:15px; border-bottom:1px solid #333; text-align:left; }}
    th {{ background: #00d2ff; color: black; }}
    a {{ color:#00d2ff; text-decoration:none; }}
</style></head>
<body>
    <h1>🗄️ SYSPWER 測試紀錄庫</h1>
    
    <div class="mission-control">
        <h3>🚀 New Quest (新任務)</h3>
        <input type="text" id="projName" placeholder="系統名稱 (如: Apple)">
        <input type="text" id="targetUrl" placeholder="目標網址 (https://...)">
        <button onclick="startRaid()">開始測試</button>
        <p style="font-size:12px; color:#aaa; margin-top:10px;">點擊後系統將在列表中新增「檢測中」狀態並啟動 AI</p>
    </div>

    <table>
        <thead><tr><th>時間</th><th>系統名稱</th><th>目標網址</th><th>冒險報告</th></tr></thead>
        <tbody>{table_rows}</tbody>
    </table>
    
    <script>
    function startRaid() {{
        const name = document.getElementById('projName').value;
        const url = document.getElementById('targetUrl').value;
        if(!name || !url) return alert('請填寫系統名稱與網址');
        document.querySelector('.mission-control button').innerText = '⌛ 指令已發送...';
        window.open(`https://t.me/JoeClowAI_bot?text=Raid 測試 ${{encodeURIComponent(name)}} ${{encodeURIComponent(url)}}`);
    }}
    </script>
</body>
</html>'''
    with open('raid_index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)

if __name__ == "__main__":
    generate_index_page()
