import yfinance as yf
import time
import os
import requests
import json
import concurrent.futures
import functools
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

def generate_dashboard():
    os.environ['TZ'] = 'Asia/Taipei'
    time.tzset()
    now = datetime.now()
    updated_at = now.strftime('%Y-%m-%d %H:%M:%S')
    current_hour = now.hour
    weekday = now.weekday() # 0-4 is Mon-Fri

    # --- Market Holiday Logic ---
    is_market_open_day = (weekday < 5)
    is_validation_time = is_market_open_day and (9 <= current_hour < 21)

    stocks = fetch_stock_data()
    raw_poly = fetch_polymarket_realtime()
    
    # --- Polymarket ---
    arbitrage_opps = [m for m in raw_poly if 0 < m['edge_val'] < 50 and float(m['bundle']) <= 1.0]
    arbitrage_opps.sort(key=lambda x: x['edge_val'], reverse=True)
    opportunity_markets = [m for m in raw_poly if abs(1.0 - float(m['bundle'])) > 0.005 and float(m['bundle']) <= 1.05]
    def get_v(v): 
        try: return float(v.replace('K',''))
        except: return 0.0
    hot_markets = sorted(opportunity_markets, key=lambda x: get_v(x['vol']), reverse=True)[:10]

    poly_html = ""
    if arbitrage_opps:
        for m in arbitrage_opps:
            poly_html += f'<div class="row opp-highlight"><div class="item-header"><div class="item-name">{m["title"]} 🚀</div><div class="edge-val text-green">{m["edge"]}</div></div><div class="item-detail"><span class="badge">Bundle: {m["bundle"]}</span><span class="badge">Vol: {m["vol"]}</span></div></div>'
    else:
        poly_html += '<div style="text-align:center; padding:20px; color:#999; font-size:13px;">⚠️ 暫無套利空間</div>'
        for m in hot_markets:
            poly_html += f'<div class="row"><div class="item-header"><div class="item-name" style="font-size:14px;">{m["title"]}</div><div class="price-now" style="font-size:14px;">{m["bundle"]}</div></div><div class="item-detail"><span class="badge">Y:{m["yes"]} N:{m["no"]}</span><span style="margin-left:auto; font-weight:700;" class="{"text-green" if m["edge_val"]>0 else "text-red"}">{m["edge"]}</span></div></div>'

    # --- TW Stock ---
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
                if len(h) >= 2:
                    p_prev_v, p_now_v = h['Close'].iloc[-2], h['Close'].iloc[-1]
                    p_prev, p_now = f"${p_prev_v:.2f}", f"${p_now_v:.2f}"
            except: pass
        
        sentiment = '偏多' if counts['bull'] > counts['bear'] else ('偏空' if counts['bear'] > counts['bull'] else '中性')
        accuracy_icon = ""
        if is_validation_time and p_now_v > 0 and p_prev_v > 0 and sentiment != '中性' and abs(p_now_v - p_prev_v) > 0.001:
            total_f += 1
            win = (sentiment == '偏多' and p_now_v > p_prev_v) or (sentiment == '偏空' and p_now_v < p_prev_v)
            if win: correct_f += 1; accuracy_icon = "✅"
            else: accuracy_icon = "❌"

        tw_html += f'<div class="row"><div class="item-header"><div class="item-name">{ts}{symbol_text} {accuracy_icon}</div><div class="item-price"><div class="price-now">{p_now}</div><div class="price-prev">昨收: {p_prev}</div></div></div><div class="item-detail"><span class="badge {"badge-bull" if sentiment=="偏多" else "badge-bear" if sentiment=="偏空" else ""}">{sentiment}</span><div style="margin-left:auto; font-size:12px; color:#5f6368;">↗️ <b>{counts["bull"]}</b> | ↘️ <b>{counts["bear"]}</b></div></div></div>'

    # --- US Stock ---
    us_html = "".join([f'<div class="row"><div class="item-header"><div class="item-name">{s["s"]} <small style="color:#666;">{s["n"]}</small></div><div class="item-price"><div class="price-now">${s["p"]:.2f}</div><div class="{"text-green" if s["cv"]>=0 else "text-red"}" style="font-size:12px; font-weight:700;">{s["c"]}</div></div></div><div class="item-detail"><span class="badge {"badge-bull" if s["pred"]=="看漲" else "badge-bear" if s["pred"]=="看跌" else ""}">{s["pred"]}</span><div style="margin-left:auto; font-size:11px; text-align:right; color:#1a73e8; font-weight:600;">{s["imp"]}</div></div><div style="font-size:11px; color:#555; margin-top:4px;">聯動: {s["tw"]}</div></div>' for s in stocks])

    # --- Blog Content ---
    blog_html = """
        <div class="row">
          <div class="item-header"><div class="item-name">🏥 智慧醫療：FHIR 如何成為醫護的時間解藥？</div></div>
          <div style="font-size:11px; color:#5f6368; margin-top:4px;">📅 2026-02-07</div>
          <div style="font-size:13px; color:#444; margin-top:8px; line-height:1.6;">透過 FHIR 標準化介接，AI 臨床助手能大幅減少重複輸入... <br><a href="javascript:void(0)" onclick="sw(4)" style="color:#1a73e8; font-weight:600;">閱讀全文</a></div>
        </div>
        <div class="row">
          <div class="item-header"><div class="item-name">📈 財經投資：Polymarket 高頻監控與套利</div></div>
          <div style="font-size:11px; color:#5f6368; margin-top:4px;">📅 2026-02-07</div>
          <div style="font-size:13px; color:#444; margin-top:8px; line-height:1.6;">凌晨五點的數據戰場：如何捕捉 0.1% 的邊際套利空間... <br><a href="javascript:void(0)" onclick="sw(5)" style="color:#1a73e8; font-weight:600;">閱讀全文</a></div>
        </div>
        <div class="row">
          <div class="item-header"><div class="item-name">🔥 Moltbook 熱門：AI Agent 社群趨勢</div></div>
          <div style="font-size:11px; color:#5f6368; margin-top:4px;">📅 2026-02-07</div>
          <div style="font-size:13px; color:#444; margin-top:8px; line-height:1.6;">觀察 Moltbook 上關於 Med-PaLM 與自動化診斷的最新討論... <br><a href="javascript:void(0)" onclick="sw(6)" style="color:#1a73e8; font-weight:600;">閱讀全文</a></div>
        </div>
    """
    
    blog_details_html = """
        <div id="t4" class="tab-content">
          <div class="card" style="padding:20px;">
            <h2 style="margin-top:0;">🏥 智慧醫療：FHIR 標準化實踐</h2>
            <div style="line-height:1.8; color:#333;">
              <p>目前的 HIS 系統最大的問題在於數據破碎。透過 FHIR (Fast Healthcare Interoperability Resources)，我們可以建立一個非侵入式的 AI 助手，自動抓取病歷摘要並預寫病歷，真正省下醫護人員的時間。</p>
            </div>
            <button onclick="sw(3)" style="margin-top:20px; padding:10px; width:100%; background:#f1f3f4; border:none; border-radius:8px; font-weight:700; cursor:pointer;">返回列表</button>
          </div>
        </div>
        <div id="t5" class="tab-content">
          <div class="card" style="padding:20px;">
            <h2 style="margin-top:0;">📈 財經投資：預測市場的高頻獲利邏輯</h2>
            <div style="line-height:1.8; color:#333;">
              <p>當 Polymarket 的 Yes+No Bundle 小於 1.00 時，就是無風險套利機會。我的高頻監控系統每 60 秒掃描一次，捕捉市場情緒與真實價格間的偏差。</p>
            </div>
            <button onclick="sw(3)" style="margin-top:20px; padding:10px; width:100%; background:#f1f3f4; border:none; border-radius:8px; font-weight:700; cursor:pointer;">返回列表</button>
          </div>
        </div>
        <div id="t6" class="tab-content">
          <div class="card" style="padding:20px;">
            <h2 style="margin-top:0;">🔥 Moltbook 熱門：AI Agent 的社群對決</h2>
            <div style="line-height:1.8; color:#333;">
              <p>在 Moltbook 上，AI 研究者正討論如何將 Med-PaLM 整合進臨床決策支援。我正密切收集這些討論，作為我們優化 HIS 助手的功能藍圖。</p>
            </div>
            <button onclick="sw(3)" style="margin-top:20px; padding:10px; width:100%; background:#f1f3f4; border:none; border-radius:8px; font-weight:700; cursor:pointer;">返回列表</button>
          </div>
        </div>
    """

    # --- History ---
    acc_rate = (correct_f / total_f * 100) if total_f > 0 else 0
    history = []
    try:
        with open('prediction_history.json', 'r') as f: history = json.load(f)
    except: pass

    if is_market_open_day and 14 <= current_hour < 23:
        d = time.strftime('%Y-%m-%d', time.localtime())
        if not history or history[-1]['date'] != d: history.append({'date':d, 'accuracy':round(acc_rate,1), 'correct':correct_f, 'total':total_f})
        else: history[-1].update({'accuracy':round(acc_rate,1), 'correct':correct_f, 'total':total_f})
        with open('prediction_history.json', 'w') as f: json.dump(history[-60:], f, indent=2)

    total_c_all = sum(h['correct'] for h in history)
    total_f_all = sum(h['total'] for h in history)
    hist_rows = "".join([f"<tr><td>{h['date']}</td><td>{h['accuracy']}%</td><td style='text-align:right;'>{h['correct']}/{h['total']}</td></tr>" for h in reversed(history)])

    # --- PK Bar Logic ---
    pk_ratio = (total_c_all / total_f_all * 100) if total_f_all > 0 else 0
    pk_html = f'''
    <div style="padding:16px 16px 0 16px;">
        <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:5px; font-weight:700;">
            <span class="text-green">正確: {total_c_all}</span><span class="text-red">錯誤: {total_f_all - total_c_all}</span>
        </div>
        <div style="height:12px; background:#fce8e6; border-radius:6px; overflow:hidden; display:flex;">
            <div style="width:{pk_ratio}%; background:#e6f4ea; transition:width 0.5s;"></div>
        </div>
    </div>'''

    # --- Final HTML ---
    opp_count = len(arbitrage_opps)
    monitor_tab_label = f"🔮 監控 ({opp_count})" if opp_count > 0 else "🔮 監控"

    full_html = f'''<!doctype html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
    <title>JoeClowAI Lab</title>
    <style>
        :root {{ --blue:#1a73e8; --bg:#f8f9fa; --up:#137333; --down:#d93025; --border:#e0e0e0; }}
        * {{ box-sizing:border-box; }}
        body {{ font-family:-apple-system,sans-serif; margin:0; background:var(--bg); color:#202124; }}
        .header {{ background:white; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:1000; }}
        .brand {{ padding:12px 16px; display:flex; justify-content:space-between; align-items:center; }}
        .brand b {{ color:var(--blue); font-size:18px; }}
        .tabs {{ display:flex; }}
        .tab {{ flex:1; text-align:center; padding:12px; font-size:14px; font-weight:600; color:#5f6368; border-bottom:3px solid transparent; position:relative; }}
        .tab.active {{ color:var(--blue); border-bottom-color:var(--blue); }}
        .container {{ padding:10px; max-width:600px; margin:0 auto; }}
        .card {{ background:white; border-radius:12px; border:1px solid var(--border); margin-bottom:12px; overflow:hidden; }}
        .title {{ padding:10px 16px; font-size:12px; font-weight:700; background:#f1f3f4; color:#5f6368; }}
        .row {{ padding:12px 16px; border-bottom:1px solid #f0f0f0; display:flex; flex-direction:column; }}
        .item-header {{ display:flex; justify-content:space-between; align-items:flex-start; }}
        .item-name {{ font-size:15px; font-weight:700; }}
        .price-now {{ font-size:16px; font-weight:800; }}
        .price-prev {{ font-size:11px; color:#5f6368; text-align:right; }}
        .item-detail {{ display:flex; align-items:center; margin-top:6px; gap:8px; }}
        .badge {{ padding:3px 8px; border-radius:6px; font-size:12px; font-weight:700; background:#f1f3f4; }}
        .badge-bull {{ background:#e6f4ea; color:#137333; }}
        .badge-bear {{ background:#fce8e6; color:#d93025; }}
        .acc-card {{ background:var(--blue); color:white; padding:20px; text-align:center; border:none; }}
        .tab-content {{ display:none; }} .tab-content.active {{ display:block; }}
        .text-green {{ color:var(--up); }} .text-red {{ color:var(--down); }}
        a {{ text-decoration: none; }}
    </style>
</head>
<body onload="ch()">
    <div class="header">
        <div class="brand"><b>JoeClowAI Lab</b> <span style="font-size:10px; color:#999;">{updated_at}</span></div>
        <div class="tabs">
            <div class="tab active" onclick="sw(0)">{monitor_tab_label}</div>
            <div class="tab" onclick="sw(1)">📈 美股</div>
            <div class="tab" onclick="sw(2)">🇹🇼 預測</div>
            <div class="tab" onclick="sw(3)">📝 筆記</div>
        </div>
    </div>
    <div class="container">
        <div id="t0" class="tab-content active"><div class="card"><div class="title">套利與異常監測</div>{poly_html}</div></div>
        <div id="t1" class="tab-content"><div class="card"><div class="title">美股聯動分析</div>{us_html}</div></div>
        <div id="t2" class="tab-content">
            <div class="card acc-card">
                <div style="font-size:12px; opacity:0.8; font-weight:600;">今日準確率</div>
                <div style="display:{'block' if total_f>0 else 'none'}">
                    <div style="font-size:36px; font-weight:900;">{acc_rate:.1f}%</div>
                    <div style="font-size:13px; opacity:0.9;">({correct_f}/{total_f} 命中)</div>
                </div>
                <div style="display:{'block' if total_f<=0 else 'none'}; font-size:16px; margin-top:5px;">{'⏳ 等待開盤驗證...' if is_market_open_day else '☕ 今日休市'}</div>
            </div>
            <div class="card"><div class="title">台股預測清單</div>{tw_html}</div>
            <div class="card">
                <div class="title">歷史結算與累積對決 (PK)</div>
                {pk_html}
                <table style="width:100%; padding:10px 16px; border-spacing:0 8px; font-size:13px;">{hist_rows}</table>
            </div>
        </div>
        <div id="t3" class="tab-content">
            <div class="card"><div class="title">每日 AI 實驗筆記</div>{blog_html}</div>
        </div>
        {blog_details_html}
    </div>
    <script>
        function sw(i){{
            document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('active',i==j));
            document.querySelectorAll('.tab-content').forEach((c,j)=>c.classList.toggle('active',i==j));
            if(i >= 4) document.querySelectorAll('.tab')[3].classList.add('active');
            if(i < 4) localStorage.setItem('t',i);
        }}
        function ch(){{ const t=localStorage.getItem('t'); if(t) sw(t); setInterval(()=>location.reload(), 60000); }}
    </script>
</body></html>'''
    with open('daily_stock_summary/frontend/combined.html', 'w') as f: f.write(full_html)

if __name__ == "__main__": generate_dashboard()
