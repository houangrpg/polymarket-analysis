import yfinance as yf
import time
import os
import requests
import json
import concurrent.futures
import functools
import glob
from datetime import datetime

@functools.lru_cache(maxsize=200)
def search_tw_ticker(name):
    try:
        overrides = {
            '台積電': '2330.TW', '鴻海': '2317.TW', '廣達': '2382.TW', 
            '技嘉': '2376.TW', '世芯-KY': '3661.TW', '大立光': '3008.TW', 
            '貿聯-KY': '3665.TW', '廣達電腦': '2382.TW'
        }
        if name in overrides: return overrides[name]
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={name}&quotesCount=10"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        for q in data.get('quotes', []):
            symbol = q.get('symbol', '')
            if symbol.endswith('.TW') or symbol.endswith('.TWO'):
                return symbol
    except: pass
    return None

def fetch_stock_data():
    tickers = ['TSLA', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AVGO', 'TSM', 'ASML', 'ARM']
    data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            p = float(info.get('regularMarketPrice') or info.get('currentPrice') or 0.0)
            pc = float(info.get('previousClose') or p)
            change = ((p - pc) / pc * 100) if pc else 0
            prediction, impact, tw = "盤整", "市場觀望", "待分析"
            if ticker in ['TSLA']:
                tw, impact = "台積電、鴻海、貿聯-KY", "電動車供應鏈受惠" if change > 1 else "需求擔憂影響"
                prediction = "看漲" if change > 1 else ("看跌" if change < -1 else "盤整")
            elif ticker in ['NVDA', 'AVGO', 'TSM', 'ASML', 'ARM']:
                tw, impact = "台積電、廣達、技嘉、世芯-KY", "AI 半導體需求強勁" if change > 1 else "半導體族群回檔"
                prediction = "看漲" if change > 1 else ("看跌" if change < -1 else "盤整")
            elif ticker in ['AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN']:
                tw, impact = "台積電、鴻海、大立光、廣達", "大型科技股資本支出" if change > 0.5 else "科技股高檔震盪"
                prediction = "看漲" if change > 0.5 else "盤整"
            data.append({
                's': ticker, 'n': info.get('longName', ticker), 'p': p, 
                'c': f"{'+' if change>=0 else ''}{change:.2f}%", 'cv': change,
                'pred': prediction, 'imp': impact, 'tw': tw
            })
        except: pass
    return data

def get_clob_price(token_id):
    try:
        r = requests.get(f"https://clob.polymarket.com/book?token_id={token_id}", timeout=5)
        book = r.json()
        if book.get('asks'): return float(book['asks'][0]['price'])
    except: pass
    return None

def fetch_polymarket_realtime():
    try:
        url = "https://gamma-api.polymarket.com/events?closed=false&limit=30&order=volume24hr&ascending=false"
        resp = requests.get(url, timeout=10)
        events = resp.json()
        results = []
        for e in events:
            markets = e.get('markets', [])
            if not markets: continue
            m = max(markets, key=lambda x: float(x.get('volume24hr', 0)), default=None)
            if not m: continue
            try:
                clob_ids = json.loads(m.get('clobTokenIds'))
                yes_ask = get_clob_price(clob_ids[0])
                no_ask = get_clob_price(clob_ids[1])
                if yes_ask and no_ask:
                    bundle = yes_ask + no_ask
                    edge = (1.0 - bundle) * 100
                    results.append({
                        'title': e.get('title', m.get('question', 'Unknown')),
                        'slug': m.get('slug', ''),
                        'yes': f"{yes_ask:.3f}",
                        'no': f"{no_ask:.3f}",
                        'bundle': f"{bundle:.3f}",
                        'edge_val': edge,
                        'edge': f"{edge:.2f}%",
                        'vol': f"{float(e.get('volume24hr', 0))/1000:.1f}K"
                    })
            except: pass
        return results
    except: return []

def load_blogs():
    cache_file = 'blog_cache.json'
    blog_dir = 'blog'
    files = glob.glob(f'{blog_dir}/*.md')
    if not files: return []
    current_mtime_sum = sum(os.path.getmtime(f) for f in files)
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                if cache_data.get('mtime_sum') == current_mtime_sum: return cache_data.get('blogs', [])
    except: pass
    blogs = []
    for f_path in files:
        try:
            with open(f_path, 'r') as f:
                content = f.read(); parts = content.split('---')
                if len(parts) >= 3:
                    header = parts[1]; body = parts[2].strip(); meta = {}
                    for line in header.strip().split('\n'):
                        if ':' in line: k, v = line.split(':', 1); meta[k.strip()] = v.strip().strip('"')
                    blogs.append({'title': meta.get('title', 'Untitled'), 'date': str(meta.get('date', '')), 'category': meta.get('category', 'General'), 'body': body, 'file': os.path.basename(f_path)})
        except: pass
    sorted_blogs = sorted(blogs, key=lambda x: x['date'], reverse=True)
    try:
        with open(cache_file, 'w') as f: json.dump({'mtime_sum': current_mtime_sum, 'blogs': sorted_blogs}, f)
    except: pass
    return sorted_blogs

def generate_dashboard():
    os.environ['TZ'] = 'Asia/Taipei'; time.tzset()
    now = datetime.now(); updated_at = now.strftime('%Y-%m-%d %H:%M:%S')
    current_hour = now.hour; weekday = now.weekday()
    is_market_open_day = (weekday < 5)
    is_validation_time = is_market_open_day and (9 <= current_hour < 21)

    stocks = fetch_stock_data(); raw_poly = fetch_polymarket_realtime()
    arbitrage_opps = [m for m in raw_poly if 0 < m['edge_val'] < 50 and float(m['bundle']) <= 1.0]
    arbitrage_opps.sort(key=lambda x: x['edge_val'], reverse=True)
    def get_v(v): 
        try: return float(v.replace('K',''))
        except: return 0.0
    hot_markets = sorted([m for m in raw_poly if float(m['bundle']) <= 1.05], key=lambda x: get_v(x['vol']), reverse=True)[:10]

    poly_html = ""
    if arbitrage_opps:
        for m in arbitrage_opps: poly_html += f'<div class="row opp-highlight"><div class="item-header"><div class="item-name">{m["title"]} 🚀</div><div class="edge-val text-green">{m["edge"]}</div></div><div class="item-detail"><span class="badge">Bundle: {m["bundle"]}</span><span class="badge">Vol: {m["vol"]}</span></div></div>'
    else:
        poly_html += '<div style="text-align:center; padding:20px; color:#999; font-size:13px;">⚠️ 暫無套利空間</div>'
        for m in hot_markets: poly_html += f'<div class="row"><div class="item-header"><div class="item-name" style="font-size:14px;">{m["title"]}</div><div class="price-now" style="font-size:14px;">{m["bundle"]}</div></div><div class="item-detail"><span class="badge">Y:{m["yes"]} N:{m["no"]}</span><span style="margin-left:auto; font-weight:700;" class="{"text-green" if m["edge_val"]>0 else "text-red"}">{m["edge"]}</span></div></div>'

    tw_stats = {}
    for s in stocks:
        for ts in [x.strip() for x in s['tw'].replace('、', ',').split(',') if x.strip()]:
            if ts not in tw_stats: tw_stats[ts] = {'bull':0, 'bear':0}
            if s['pred'] == '看漲': tw_stats[ts]['bull'] += 1
            elif s['pred'] == '看跌': tw_stats[ts]['bear'] += 1
    
    sorted_tw = sorted(tw_stats.items(), key=lambda x: (x[1]['bull'], -x[1]['bear']), reverse=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        tickers = list(ex.map(search_tw_ticker, [ts for ts, _ in sorted_tw]))

    tw_html, total_f, correct_f = "", 0, 0
    for (ts, counts), ticker in zip(sorted_tw, tickers):
        p_now, p_prev, p_now_v, p_prev_v = "-", "-", 0, 0
        symbol_text = f" ({ticker.replace('.TW','').replace('.TWO','')})" if ticker else ""
        if ticker:
            try:
                h = yf.Ticker(ticker).history(period="5d")
                if len(h) >= 2: p_prev_v, p_now_v = h['Close'].iloc[-2], h['Close'].iloc[-1]; p_prev, p_now = f"${p_prev_v:.2f}", f"${p_now_v:.2f}"
            except: pass
        sentiment = '偏多' if counts['bull'] > counts['bear'] else ('偏空' if counts['bear'] > counts['bull'] else '中性')
        accuracy_icon = ""
        if is_validation_time and p_now_v > 0 and p_prev_v > 0 and sentiment != '中性' and abs(p_now_v - p_prev_v) > 0.001:
            total_f += 1; win = (sentiment == '偏多' and p_now_v > p_prev_v) or (sentiment == '偏空' and p_now_v < p_prev_v)
            if win: correct_f += 1; accuracy_icon = "✅"
            else: accuracy_icon = "❌"
        tw_html += f'''
            <div class="row">
                <div class="item-header" style="display: flex; justify-content: space-between; align-items: center; width: 100%; position: relative;">
                    <div class="item-name" style="z-index: 1;">{ts}{symbol_text} {accuracy_icon}</div>
                    <div class="price-now {'text-green' if p_now_v > p_prev_v else 'text-red' if p_now_v < p_prev_v else ''}" style="position: absolute; left: 50%; transform: translateX(-50%); font-size:32px; font-weight:900;">{p_now}</div>
                    <div class="item-price" style="text-align:right; z-index: 1;">
                        <div class="price-prev" style="font-size:12px; color:#666;">昨收: {p_prev}</div>
                    </div>
                </div>
                <div class="item-detail" style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                    <span class="badge {'badge-bull' if sentiment=='偏多' else 'badge-bear' if sentiment=='偏空' else ''}">{sentiment}</span>
                    <div style="font-size:12px; color:#5f6368;">↗️ <b>{counts["bull"]}</b> | ↘️ <b>{counts["bear"]}</b></div>
                </div>
            </div>'''

    us_html = "".join([f'<div class="row"><div class="item-header"><div class="item-name">{s["s"]} <small style="color:#666;">{s["n"]}</small></div><div class="item-price"><div class="price-now">${s["p"]:.2f}</div><div class="{"text-green" if s["cv"]>=0 else "text-red"}" style="font-size:12px; font-weight:700;">{s["c"]}</div></div></div><div class="item-detail"><span class="badge {"badge-bull" if s["pred"]=="看漲" else "badge-bear" if s["pred"]=="看跌" else ""}">{s["pred"]}</span><div style="margin-left:auto; font-size:11px; text-align:right; color:#1a73e8; font-weight:600;">{s["imp"]}</div></div><div style="font-size:11px; color:#555; margin-top:4px;">聯動: {s["tw"]}</div></div>' for s in stocks])

    blogs = load_blogs(); blog_list_html = ""; blog_details_html = ""
    for i, b in enumerate(blogs):
        safe_body = b['body'].replace('\n', '<br>')
        blog_list_html += f'<div class="row"><div class="item-header"><div class="item-name">{b["title"]}</div></div><div style="font-size:11px; color:#5f6368; margin-top:4px;">📅 {b["date"]} | 🏷️ {b["category"]}</div><div style="font-size:13px; color:#444; margin-top:8px; line-height:1.6;">{b["body"][:60]}... <br><a href="javascript:void(0)" onclick="sw({i+5})" style="color:#1a73e8; font-weight:600;">閱讀全文</a></div></div>'
        blog_details_html += f'<div id="t{i+5}" class="tab-content"><div class="card" style="padding:20px;"><h2 style="margin-top:0;">{b["title"]}</h2><div style="font-size:12px; color:#666; margin-bottom:15px;">發佈日期：{b["date"]} | 分類：{b["category"]}</div><div style="line-height:1.8; color:#333;">{safe_body}</div><button onclick="sw(3)" style="margin-top:20px; padding:10px; width:100%; background:#f1f3f4; border:none; border-radius:8px; font-weight:700; cursor:pointer;">返回列表</button></div></div>'

    history = []
    try:
        with open('prediction_history.json', 'r') as f: history = json.load(f)
    except: pass
    if is_market_open_day and 14 <= datetime.now().hour < 23:
        d = time.strftime('%Y-%m-%d', time.localtime())
        if not history or history[-1]['date'] != d: history.append({'date':d, 'accuracy':round((correct_f/total_f*100) if total_f>0 else 0,1), 'correct':correct_f, 'total':total_f})
        else: history[-1].update({'accuracy':round((correct_f/total_f*100) if total_f>0 else 0,1), 'correct':correct_f, 'total':total_f})
        with open('prediction_history.json', 'w') as f: json.dump(history[-60:], f, indent=2)
    hist_rows = "".join([f"<tr><td>{h['date']}</td><td>{h['accuracy']}%</td><td style='text-align:right;'>{h['correct']}/{h['total']}</td></tr>" for h in reversed(history)])

    status_data = {}
    try:
        with open('dashboard/status.json', 'r') as f: status_data = json.load(f)
    except: status_data = {"system_status": "Online", "last_updated": updated_at, "todos": [], "in_progress": [], "done": [], "scheduled_tasks": []}

    status_html = f'''
        <div class="card"><div class="title">系統狀態</div><div style="padding:16px;"><span class="status-badge status-online">系統正常運作中 ({status_data.get("system_status", "Online")})</span><p style="font-size:12px; color:#666;">最後更新：{status_data.get("last_updated", updated_at)}</p></div></div>
        <div class="card"><div class="title">執行進度 (In Progress)</div><ul style="padding:0 16px;">{"".join([f"<li>{x}</li>" for x in status_data.get("in_progress", [])])}</ul></div>
        <div class="card"><div class="title">待辦事項 (To-Do)</div><ul style="padding:0 16px;">{"".join([f"<li>{x}</li>" for x in status_data.get("todos", [])])}</ul></div>
        <div class="card"><div class="title">已完成事項 (Done)</div><ul style="padding:0 16px;">{"".join([f"<li>{x}</li>" for x in status_data.get("done", [])])}</ul></div>
        <div class="card"><div class="title">自動排程 (Scheduled)</div><ul style="padding:0 16px;">{"".join([f"<li>{x['task']} <small style='color:#888;'>({x['time']})</small></li>" for x in status_data.get("scheduled_tasks", [])])}</ul></div>
    '''

    # --- Kindle Auto Page (Force Refresh & Landscape) ---
    kindle_auto_html = f'''<!doctype html><html lang="zh-TW"><head><meta charset="utf-8"><meta http-equiv="refresh" content="60"><meta name="viewport" content="width=1072, user-scalable=no"><title>Kindle Dash</title><style>
        body {{ background:white; color:black; margin:0; padding:0; width:1072px; height:1448px; overflow:hidden; position: absolute; font-family:serif; }} 
        .rotate {{ 
            -webkit-transform: rotate(90deg); 
            -webkit-transform-origin: center center;
            transform: rotate(90deg); 
            transform-origin: center center; 
            width: 1250px; 
            height: 1000px; 
            position: absolute; 
            top: 50%; 
            left: 55%; 
            margin-top: -500px; 
            margin-left: -625px; 
            background: white;
            display: block;
        }}
        .header-section {{ height: 180px; border-bottom: 5px solid black; text-align: center; padding: 10px; box-sizing: border-box; width: 1250px; }}
        .data-section {{ height: 820px; width: 1250px; }}
        table {{ width: 1250px; height: 820px; border-collapse: collapse; table-layout: fixed; }}
        td {{ vertical-align: top; border-right: 5px solid black; padding: 15px; box-sizing: border-box; overflow: hidden; }}
        td:last-child {{ border-right: none; }}
        .k-time {{ font-size: 140px; font-weight: 900; margin: 0; line-height: 1; }}
        .k-date {{ font-size: 34px; margin-top: 5px; font-weight: bold; }}
        .k-title {{ font-size: 34px; font-weight: bold; background: black; color: white; padding: 8px; margin-bottom: 15px; text-align: center; }}
        .k-item {{ font-size: 30px; margin-bottom: 15px; border-bottom: 3px solid black; padding-bottom: 8px; overflow: hidden; white-space: nowrap; }}
        .k-item b {{ float: right; margin-left: 10px; }}
        .k-status-box {{ font-size: 30px; line-height: 1.4; }}
        .blog-item {{ font-size: 26px; margin-bottom: 12px; border-bottom: 1px solid #666; padding-bottom: 8px; }}
    </style></head><body><div class="rotate">
        <div class="header-section">
            <div class="k-time">{datetime.now().strftime('%H:%M')}</div>
            <div class="k-date">{datetime.now().strftime('%Y-%m-%d')} | v2.4</div>
        </div>
        <div class="data-section">
            <table cellspacing="0" cellpadding="0" border="0">
                <tr>
                    <td width="30%">
                        <div class="k-title">🔮 監控</div>
                        {"".join([f'<div class="k-item">{m["title"][:8]}<b>{m["edge"]}</b></div>' for m in hot_markets[:6]])}
                    </td>
                    <td width="70%">
                        <div class="k-title">🛠️ 進度 & 筆記</div>
                        <div class="k-status-box">
                            <b>In Progress:</b><br>
                            {"".join([f'• {x[:35]}<br>' for x in status_data.get("in_progress", [])])}
                            <hr style="border:1px solid black; margin:10px 0;">
                            <b>實驗筆記:</b><br>
                            {"".join([f'<div class="blog-item">• {b["title"][:30]}</div>' for b in blogs[:2]])}
                        </div>
                    </td>
                </tr>
            </table>
        </div>
    </div></body></html>'''
    with open('daily_stock_summary/frontend/kindle_auto.html', 'w') as f: f.write(kindle_auto_html)

    full_html = f'''<!doctype html><html lang="zh-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover"><title>JoeClowAI Lab</title><style>:root {{ --blue:#1a73e8; --bg:#f8f9fa; --up:#137333; --down:#d93025; --border:#e0e0e0; }} * {{ box-sizing:border-box; }} body {{ font-family:-apple-system,sans-serif; margin:0; background:var(--bg); color:#202124; }} .header {{ background:white; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:1000; }} .brand {{ padding:12px 16px; display:flex; justify-content:space-between; align-items:center; }} .brand b {{ color:var(--blue); font-size:18px; }} .tabs {{ display:flex; }} .tab {{ flex:1; text-align:center; padding:12px; font-size:14px; font-weight:600; color:#5f6368; border-bottom:3px solid transparent; position:relative; cursor:pointer; }} .tab.active {{ color:var(--blue); border-bottom-color:var(--blue); }} .container {{ padding:10px; max-width:1200px; margin:0 auto; }} .card {{ background:white; border-radius:12px; border:1px solid var(--border); margin-bottom:12px; overflow:hidden; }} .title {{ padding:10px 16px; font-size:12px; font-weight:700; background:#f1f3f4; color:#5f6368; }} .row {{ padding:12px 16px; border-bottom:1px solid #f0f0f0; display:flex; flex-direction:column; }} .item-header {{ display:flex; justify-content:space-between; align-items:flex-start; }} .item-name {{ font-size:15px; font-weight:700; }} .price-now {{ font-size:16px; font-weight:800; }} .price-prev {{ font-size:11px; color:#5f6368; text-align:right; }} .item-detail {{ display:flex; align-items:center; margin-top:6px; gap:8px; }} .badge {{ padding:3px 8px; border-radius:6px; font-size:12px; font-weight:700; background:#f1f3f4; }} .badge-bull {{ background:#e6f4ea; color:#137333; }} .badge-bear {{ background:#fce8e6; color:#d93025; }} .acc-card {{ background:var(--blue); color:white; padding:20px; text-align:center; border:none; }} .tab-content {{ display:none; }} .tab-content.active {{ display:block; }} .text-green {{ color:var(--up); }} .text-red {{ color:var(--down); }} .status-badge {{ display:inline-block; padding:5px 12px; border-radius:20px; font-weight:bold; font-size:14px; }} .status-online {{ background:#e6f4ea; color:#137333; }} ul {{ list-style:none; padding:0; }} li {{ padding:8px 0; border-bottom:1px solid #f9f9f9; display:flex; align-items:center; font-size:14px; }} li::before {{ content:"•"; color:#1a73e8; font-weight:bold; margin-right:10px; }}</style></head><body onload="ch()"><div class="header"><div class="brand"><b>JoeClowAI Lab</b> <span style="font-size:10px; color:#999;">{updated_at}</span></div><div class="tabs"><div class="tab active" onclick="sw(0)">🔮 監控</div><div class="tab" onclick="sw(1)">📈 美股</div><div class="tab" onclick="sw(2)">🇹🇼 預測</div><div class="tab" onclick="sw(3)">📝 筆記</div><div class="tab" onclick="sw(4)">🛠️ 狀態</div></div></div><div class="container"><div id="t0" class="tab-content active"><div class="card"><div class="title">套利與異常監測</div>{poly_html}</div></div><div id="t1" class="tab-content"><div class="card"><div class="title">美股聯動分析</div>{us_html}</div></div><div id="t2" class="tab-content"><div class="card acc-card"><div style="font-size:12px; opacity:0.8; font-weight:600;">今日準確率</div><div style="display:{'block' if total_f>0 else 'none'}"><div style="font-size:36px; font-weight:900;">{(correct_f/total_f*100) if total_f>0 else 0:.1f}%</div><div style="font-size:13px; opacity:0.9;">({correct_f}/{total_f} 命中)</div></div><div style="display:{'block' if total_f<=0 else 'none'}; font-size:16px; margin-top:5px;">{'⏳ 等待開盤驗證...' if is_market_open_day else '☕ 今日休市'}</div></div><div class="card"><div class="title">台股預測清單</div>{tw_html}</div><div class="card"><div class="title">歷史結算與累積對決 (PK)</div><table style="width:100%; padding:10px 16px; border-spacing:0 8px; font-size:13px;">{hist_rows}</table></div></div><div id="t3" class="tab-content"><div class="card"><div class="title">AI 實驗筆記歷史</div>{blog_list_html}</div></div><div id="t4" class="tab-content">{status_html}</div>{blog_details_html}</div><script>function sw(i){{document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('active',i==j));document.querySelectorAll('.tab-content').forEach((c,j)=>c.classList.toggle('active',i==j));if(i>=5)document.querySelectorAll('.tab')[3].classList.add('active');if(i<5)localStorage.setItem('t',i);}}function ch(){{const t=localStorage.getItem('t');if(t)sw(t);setInterval(()=>location.reload(),60000);}}</script></body></html>'''
    with open('combined.html', 'w') as f: f.write(full_html)

if __name__ == "__main__": generate_dashboard()
