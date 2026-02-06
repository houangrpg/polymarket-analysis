import yfinance as yf
import time
import os
import requests
import json
import concurrent.futures
import functools

# 全域快取
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
        if book.get('asks'):
            return float(book['asks'][0]['price'])
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
                token_ids_raw = m.get('clobTokenIds')
                if not token_ids_raw: continue
                clob_ids = json.loads(token_ids_raw)
                if len(clob_ids) < 2: continue
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

def generate_dashboard():
    # 修正：優先設定時區
    os.environ['TZ'] = 'Asia/Taipei'
    time.tzset()
    updated_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    current_hour = int(time.strftime('%H', time.localtime()))
    is_validation_time = (current_hour >= 9 and current_hour < 21)

    stocks = fetch_stock_data()
    raw_poly = fetch_polymarket_realtime()
    
    # 篩選邏輯
    arbitrage_opps = [m for m in raw_poly if 0 < m['edge_val'] < 50 and float(m['bundle']) <= 1.0]
    arbitrage_opps.sort(key=lambda x: x['edge_val'], reverse=True)
    
    opportunity_markets = [m for m in raw_poly if abs(1.0 - float(m['bundle'])) > 0.005 and float(m['bundle']) <= 1.05]
    if len(opportunity_markets) < 5:
        opportunity_markets = [m for m in raw_poly if abs(1.0 - float(m['bundle'])) > 0.002 and float(m['bundle']) <= 1.05]
    
    def get_vol(v): 
        try: return float(v.replace('K',''))
        except: return 0.0
    hot_markets = sorted(opportunity_markets, key=lambda x: get_vol(x['vol']), reverse=True)[:10]

    # 生成 Polymarket HTML
    poly_html = ''
    if not arbitrage_opps:
        poly_html += '<tr><td colspan="5" style="text-align:center; background:#fff3e0; color:#e65100; padding:10px;">⚠️ 暫無即時套利空間</td></tr>'
        poly_html += '<tr><td colspan="5" style="background:#e8f0fe; color:#1a73e8; font-weight:700; padding:8px 12px;">📊 異常波動監測</td></tr>'
        for m in hot_markets:
            link = f"https://polymarket.com/market/{m['slug']}"
            edge_style = 'class="text-green"' if m['edge_val'] > 0 else 'style="color:#d93025;"'
            poly_html += f'<tr><td data-label="預測市場"><a href="{link}" target="_blank">{m["title"]}</a></td><td class="val">{m["yes"]}/{m["no"]}</td><td class="val">{m["bundle"]}</td><td class="val"><b {edge_style}>{m["edge"]}</b></td><td class="val">{m["vol"]}</td></tr>'
    else:
        for m in arbitrage_opps:
            link = f"https://polymarket.com/market/{m['slug']}"
            poly_html += f'<tr class="opp-highlight"><td data-label="預測市場"><a href="{link}" target="_blank"><b>{m["title"]} 🚀</b></a></td><td class="val">{m["yes"]}/{m["no"]}</td><td class="val">{m["bundle"]}</td><td class="val text-green"><b>{m["edge"]}</b></td><td class="val">{m["vol"]}</td></tr>'

    # 台股統計與預測
    tw_stats = {}
    for s in stocks:
        tw_stocks = [x.strip() for x in s['tw'].replace('、', ',').split(',')]
        for ts in tw_stocks:
            if not ts: continue
            if ts not in tw_stats: tw_stats[ts] = {'bull':0, 'bear':0, 'neutral':0}
            if s['pred'] == '看漲': tw_stats[ts]['bull'] += 1
            elif s['pred'] == '看跌': tw_stats[ts]['bear'] += 1
            else: tw_stats[ts]['neutral'] += 1

    tw_html = ''
    total_forecasts = 0
    correct_forecasts = 0
    sorted_tw = sorted(tw_stats.items(), key=lambda x: (x[1]['bull'], -x[1]['bear']), reverse=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        names = [ts for ts, _ in sorted_tw]
        tickers = list(ex.map(search_tw_ticker, names))
    
    for (ts, counts), ticker in zip(sorted_tw, tickers):
        p_now, p_prev, p_now_v, p_prev_v = "-", "-", 0, 0
        if ticker:
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if len(hist) >= 2:
                    p_prev_v, p_now_v = hist['Close'].iloc[-2], hist['Close'].iloc[-1]
                    p_prev, p_now = f"${p_prev_v:.2f}", f"${p_now_v:.2f}"
            except: pass
        
        sentiment = '偏多' if counts['bull'] > counts['bear'] else ('偏空' if counts['bear'] > counts['bull'] else '中性')
        accuracy_icon = ""
        # 核心：僅在驗證時間且價格有變動時才判定
        if is_validation_time and p_now_v > 0 and p_prev_v > 0 and sentiment != '中性' and abs(p_now_v - p_prev_v) > 0.001:
            total_forecasts += 1
            correct = (sentiment == '偏多' and p_now_v > p_prev_v) or (sentiment == '偏空' and p_now_v < p_prev_v)
            if correct:
                correct_forecasts += 1
                accuracy_icon = "✅"
            else: accuracy_icon = "❌"

        tw_html += f'<tr><td><b>{ts} {accuracy_icon}</b></td><td class="val"><small>昨收:{p_prev}</small><br><b>現價:{p_now}</b></td><td class="val text-green">{counts["bull"]}</td><td class="val text-red">{counts["bear"]}</td><td class="val"><b>{sentiment}</b></td></tr>'

    # 準確率與歷史
    acc_rate = (correct_forecasts / total_forecasts * 100) if total_forecasts > 0 else 0
    history = []
    try:
        with open('prediction_history.json', 'r') as f: history = json.load(f)
    except: pass

    # 收盤結算
    if 14 <= current_hour < 23:
        today_str = time.strftime('%Y-%m-%d', time.localtime())
        if not history or history[-1]['date'] != today_str:
            history.append({'date':today_str, 'accuracy':round(acc_rate,1), 'correct':correct_forecasts, 'total':total_forecasts})
        else:
            history[-1].update({'accuracy':round(acc_rate,1), 'correct':correct_forecasts, 'total':total_forecasts})
        with open('prediction_history.json', 'w') as f: json.dump(history[-60:], f, indent=2)

    total_c_all = sum(h['correct'] for h in history)
    total_f_all = sum(h['total'] for h in history)
    history_rows = "".join([f"<tr><td>{h['date']}</td><td class='val'>{h['accuracy']}%</td><td class='val'>{h['correct']}/{h['total']}</td></tr>" for h in reversed(history)])

    accuracy_html = f'''
    <div class="card" style="padding:16px; background:#e8f0fe; border-left:5px solid #1a73e8; margin-bottom:20px; position:relative;">
        <div style="font-size:12px; color:#5f6368; font-weight:600;">今日預測準確度分析</div>
        <div style="display:{'flex' if total_forecasts > 0 else 'none'}; align-items:baseline; gap:10px; margin-top:8px;">
            <span style="font-size:32px; font-weight:800; color:#1a73e8;">{acc_rate:.1f}%</span>
            <span style="font-size:14px; color:#70757a;">({correct_forecasts}/{total_forecasts} 命中)</span>
        </div>
        <div style="display:{'none' if total_forecasts > 0 else 'block'}; margin-top:8px; font-size:16px; color:#70757a;">⏳ 等待台股開盤驗證預測...</div>
        <div onclick="toggleHistory()" style="position:absolute; right:16px; top:16px; cursor:pointer; background:white; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:1px solid #ddd;">ℹ️</div>
        <div id="history-panel" style="display:none; margin-top:16px; border-top:1px solid #d2e3fc; padding-top:16px;">
            <div style="background:white; border-radius:8px; padding:10px; margin-bottom:10px;">
                <div style="font-size:11px; font-weight:700;">累積 PK</div>
                <div style="height:20px; background:#fce8e6; border-radius:10px; overflow:hidden; display:flex;">
                    <div style="width:{(total_c_all/total_f_all*100) if total_f_all>0 else 0}%; background:#e6f4ea; color:#137333; font-size:10px; padding-left:8px;">正確:{total_c_all}</div>
                </div>
            </div>
            <table style="width:100%; font-size:12px;">{history_rows}</table>
        </div>
    </div>'''

    # 美股 HTML
    stock_html = "".join([f'<tr><td><b>{s["s"]}</b><br><small>{s["n"]}</small></td><td class="val"><b>${s["p"]:.2f}</b></td><td class="val {"text-green" if s["cv"]>=0 else "text-red"}">{s["c"]}</td><td><span class="badge">預測:{s["pred"]}</span><br><small>{s["tw"]}</small></td></tr>' for s in stocks])

    # 最終 HTML
    full_html = f'''<!doctype html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <title>JoeClowAI - 監控</title>
    <style>
        :root {{ --blue:#1a73e8; --bg:#f1f3f4; --up:#137333; --down:#d93025; }}
        body {{ font-family:sans-serif; margin:0; background:var(--bg); }}
        .header {{ background:white; border-bottom:1px solid #dadce0; position:sticky; top:0; z-index:100; }}
        .tabs {{ display:flex; }} .tab {{ flex:1; text-align:center; padding:14px; color:#5f6368; border-bottom:3px solid transparent; cursor:pointer; }}
        .tab.active {{ color:var(--blue); border-bottom-color:var(--blue); }}
        .container {{ padding:12px; max-width:900px; margin:0 auto; }}
        .card {{ background:white; border-radius:12px; border:1px solid #dadce0; margin-bottom:20px; overflow:hidden; }}
        table {{ width:100%; border-collapse:collapse; }} td, th {{ padding:12px; border-bottom:1px solid #eee; font-size:14px; }}
        .val {{ text-align:right; }} .text-green {{ color:var(--up); }} .text-red {{ color:var(--down); }}
        .tab-content {{ display:none; }} .tab-content.active {{ display:block; }}
        @media (max-width:600px) {{ td {{ display:block; text-align:right; }} td:before {{ content:attr(data-label); float:left; color:#70757a; }} }}
    </style>
</head>
<body onload="checkReload()">
    <div class="header">
        <div style="padding:10px 16px; font-weight:700; color:var(--blue);">JoeClowAI <span style="font-size:10px; color:#999; font-weight:400;">{updated_at}</span></div>
        <div class="tabs">
            <div class="tab active" onclick="sw(0)">🔮 套利</div>
            <div class="tab" onclick="sw(1)">📈 美股</div>
            <div class="tab" onclick="sw(2)">🇹🇼 台股預測</div>
        </div>
    </div>
    <div class="container">
        <div id="t0" class="tab-content active"><div class="card"><table>{poly_html}</table></div></div>
        <div id="t1" class="tab-content"><div class="card"><table>{stock_html}</table></div></div>
        <div id="t2" class="tab-content">{accuracy_html}<div class="card"><table>{tw_html}</table></div></div>
    </div>
    <script>
        function sw(idx){{
            document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', i === idx));
            document.querySelectorAll('.tab-content').forEach((c, i) => c.classList.toggle('active', i === idx));
            localStorage.setItem('tab', idx);
        }}
        function checkReload() {{
            const t = localStorage.getItem('tab'); if(t) sw(parseInt(t));
            setInterval(() => {{ location.href = location.pathname + "?t=" + Date.now(); }}, 60000);
        }}
        function toggleHistory() {{ const p = document.getElementById('history-panel'); p.style.display = p.style.display === 'none' ? 'block' : 'none'; }}
    </script>
</body></html>'''
    with open('daily_stock_summary/frontend/combined.html', 'w') as f: f.write(full_html)

if __name__ == "__main__": generate_dashboard()
