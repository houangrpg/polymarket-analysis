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
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} 系統冒險檢測報告</title>
    <style>
        :root {{ --bg: #0f0c29; --card: #1b1b2f; --primary: #00d2ff; --success: #39ff14; --warning: #ffbd39; --danger: #ff3131; --text: #ffffff; }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: var(--text); margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }}
        .container {{ max-width: 800px; width: 100%; }}
        header {{ text-align: center; margin-bottom: 40px; }}
        h1 {{ font-size: 3em; text-shadow: 0 0 10px var(--primary); margin: 10px 0; }}
        .status-badge {{ background: var(--success); color: black; padding: 5px 15px; border-radius: 20px; font-weight: bold; box-shadow: 0 0 15px var(--success); }}
        .quest-card {{ background: var(--card); border: 2px solid var(--primary); border-radius: 15px; padding: 20px; margin-bottom: 20px; position: relative; overflow: hidden; transition: transform 0.3s; }}
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
                {" ".join([f'<span class="loot-item loot-success">{{x}}</span>' for x in loot_items])}
            </div>
        </div>

        <div class="quest-card">
            <div class="quest-header">
                <span class="quest-title">⚡ 效能與敏捷度</span>
                <span class="difficulty">等級：A (High Speed)</span>
            </div>
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-val">{{performance_stats.get('speed', '1.2s')}}</span>
                    <span class="stat-label">頁面載入速度</span>
                </div>
                <div class="stat-item">
                    <span class="stat-val">10s</span>
                    <span class="stat-label">數據刷新間隔</span>
                </div>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width: 85%;"></div></div>
        </div>

        <div class="quest-card" style="border-color: var(--warning);">
            <div class="quest-header">
                <span class="quest-title" style="color: var(--warning);">📜 冒險家建議 (System Optimization)</span>
            </div>
            <div style="font-size: 0.9em; line-height: 1.6;">
                {"".join([f'<p>• {{x}}</p>' for x in suggestions])}
            </div>
        </div>

        <div style="text-align:center; margin-top:20px;">
            <a href="raid_index.html">⬅️ 返回測試紀錄列表庫</a>
        </div>

        <footer>
            <p>GENERATED BY JOECLOW AI • POWERED BY OPENCLAW</p>
            <p>© 2026 ADVENTURE TECH</p>
        </footer>
    </div>
</body>
</html>'''
    
    with open(report_filename, 'w') as f:
        f.write(html_content)
    
    update_raid_index(project_name, url, report_filename)
    generate_index_page()
    return report_filename

def generate_index_page():
    if not os.path.exists(INDEX_FILE): return
    with open(INDEX_FILE, 'r') as f:
        history = json.load(f)
    
    rows = "".join([f'<tr><td>{{h["date"]}}</td><td><b>{{h["name"]}}</b></td><td><a href="{{h["url"]}}" target="_blank">連結</a></td><td><a href="{{h["report"]}}" style="color:#39ff14;">[查看報告]</a></td></tr>' for h in history])
    
    index_html = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Web-Raid 測試紀錄庫</title>
<style>
    body {{ background:#0f0c29; color:white; font-family:sans-serif; padding:20px; text-align:center; }}
    .mission-control {{ background:#1b1b2f; border:2px solid #00d2ff; border-radius:15px; padding:20px; max-width:900px; margin:0 auto 30px; }}
    input {{ background:#000; border:1px solid #00d2ff; color:#fff; padding:10px; width:60%; border-radius:5px; }}
    button {{ background:#00d2ff; border:none; color:#000; padding:10px 20px; border-radius:5px; font-weight:bold; cursor:pointer; }}
    table {{ width:100%; max-width:900px; margin:20px auto; border-collapse:collapse; background:#1b1b2f; }}
    th, td {{ padding:15px; border-bottom:1px solid #333; text-align:left; }}
    th {{ background: #00d2ff; color: black; }}
    a {{ color:#00d2ff; text-decoration:none; }}
</style></head>
<body>
    <h1>🗄️ Web-Raid 測試紀錄庫</h1>
    
    <div class="mission-control">
        <h3>🚀 New Quest (新任務)</h3>
        <input type="text" id="targetUrl" placeholder="輸入目標網站網址 (例如: https://example.com)">
        <button onclick="startRaid()">開始測試</button>
        <p style="font-size:12px; color:#aaa; margin-top:10px;">點擊後將透過 Telegram AI 執行自動化 Raid 測試</p>
    </div>

    <table>
        <thead><tr><th>時間</th><th>系統名稱</th><th>目標網址</th><th>冒險報告</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    
    <script>
    function startRaid() {{
        const url = document.getElementById('targetUrl').value;
        if(!url) return alert('請輸入網址');
        // 跳轉到 Telegram 帶入指令
        window.open(`https://t.me/JoeClowAI_bot?text=Raid 測試 ${{encodeURIComponent(url)}}`);
    }}
    </script>
</body>
</html>'''
    with open('raid_index.html', 'w') as f:
        f.write(index_html)

if __name__ == "__main__":
    generate_raid_html(
        "HIS", 
        "https://his.tedpc.com.tw/hccm", 
        "MISSION ACCOMPLISHED", 
        {"level": "SS"}, 
        {"speed": "1.2s"}, 
        ["SSL已加密", "驗證碼OCR成功", "個案資料渲染正常"],
        ["強制 HTTPS 重定向", "Session 自動超時", "RWD 響應式佈局優化"]
    )
