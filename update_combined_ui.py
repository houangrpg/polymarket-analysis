import yfinance as yf
import time
import os
import requests
import json
import concurrent.futures

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
    print("Fetching Polymarket Gamma API...")
    try:
        # 獲取成交量前 40 的市場以確保涵蓋套利機會
        url = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=40&order=volume24hrClob&dir=desc"
        resp = requests.get(url, timeout=10)
        markets = resp.json()
        
        results = []
        
        def process_market(m):
            try:
                clob_ids = json.loads(m.get('clobTokenIds', '[]'))
                if len(clob_ids) < 2: return None
                
                # 同時獲取 Yes 和 No 的即時 Ask
                yes_ask = get_clob_price(clob_ids[0])
                no_ask = get_clob_price(clob_ids[1])
                
                if yes_ask and no_ask:
                    bundle = yes_ask + no_ask
                    edge = (1.0 - bundle) * 100
                    return {
                        'title': m['question'],
                        'yes': f"{yes_ask:.3f}",
                        'no': f"{no_ask:.3f}",
                        'bundle': f"{bundle:.3f}",
                        'edge_val': edge,
                        'edge': f"{edge:.2f}%",
                        'vol': f"{float(m.get('volume24hrClob', 0))/1000:.1f}K"
                    }
            except: pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_market = {executor.submit(process_market, m): m for m in markets}
            for future in concurrent.futures.as_completed(future_to_market):
                res = future.result()
                if res: results.append(res)
        
        # 獲利優先排序
        results.sort(key=lambda x: x['edge_val'], reverse=True)
        return results[:20] # 取前 20 名
    except Exception as e:
        print(f"Polymarket fetch error: {e}")
        return []

def generate_dashboard():
    print("Starting Dashboard Update...")
    updated_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    
    # 獲取即時數據
    stocks = fetch_stock_data()
    poly_markets = fetch_polymarket_realtime()
    
    stock_html = ''
    for s in stocks:
        c_cls = 'text-green' if s['cv'] >= 0 else 'text-red'
        p_cls = 'badge-bull' if s['pred'] == '看漲' else ('badge-red' if s['pred'] == '看跌' else 'badge-neutral')
        stock_html += f'''
        <tr>
            <td data-label="標的"><div class="m-cell"><b>{s['s']}</b><br><small>{s['n']}</small></div></td>
            <td data-label="價格" class="mono val"><b>${s['p']:.2f}</b></td>
            <td data-label="漲跌" class="mono val {c_cls}">{s['c']}</td>
            <td data-label="聯動預測">
                <span class="badge {p_cls}">{s['pred']}</span>
                <div class="tw-text">{s['tw']}</div>
                <div class="imp-text">{s['imp']}</div>
            </td>
        </tr>'''

    poly_html = ''
    for m in poly_markets:
        # 只有真正有獲利空間的才高亮（Edge > 0）
        opp_cls = 'opp-highlight' if m['edge_val'] > 0 else ''
        edge_cls = 'text-green' if m['edge_val'] > 0 else ('text-red' if m['edge_val'] < -0.5 else '')
        
        poly_html += f'''
        <tr class="{opp_cls}">
            <td data-label="預測市場"><div class="q-text">{m['title']}</div></td>
            <td data-label="Yes / No" class="mono val">{m['yes']} / {m['no']}</td>
            <td data-label="總價" class="mono val">{m['bundle']}</td>
            <td data-label="獲利 (Edge)" class="mono val"><b class="{edge_cls}">{m['edge']}</b></td>
            <td data-label="成交量" class="val">{m['vol']}</td>
        </tr>'''

    html = f'''<!doctype html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>OpenClaw Pro - 獲利監控</title>
    <style>
        :root {{ --blue: #1a73e8; --bg: #f1f3f4; --border: #dadce0; --up: #137333; --down: #d93025; }}
        body {{ font-family: -apple-system, sans-serif; margin: 0; background: var(--bg); color: #202124; }}
        .header {{ background: white; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }}
        .header-top {{ padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }}
        .tabs {{ display: flex; background: white; }}
        .tab {{ flex: 1; text-align: center; padding: 14px; font-size: 14px; font-weight: 500; color: #5f6368; border-bottom: 3px solid transparent; }}
        .tab.active {{ color: var(--blue); border-bottom-color: var(--blue); }}
        .container {{ padding: 12px; max-width: 950px; margin: 0 auto; }}
        .tab-content {{ display: none; }} .tab-content.active {{ display: block; }}
        .card {{ background: white; border-radius: 12px; border: 1px solid var(--border); overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #f8f9fa; padding: 12px; text-align: left; font-size: 11px; color: #5f6368; border-bottom: 1px solid var(--border); }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
        .val {{ text-align: right; }} .mono {{ font-family: "SF Mono", monospace; }}
        .text-green {{ color: var(--up); font-weight: 600; }} .text-red {{ color: var(--down); font-weight: 600; }}
        .badge {{ padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .badge-bull {{ background: #e6f4ea; color: #137333; }}
        .badge-red {{ background: #fce8e6; color: #d93025; }}
        .badge-neutral {{ background: #f1f3f4; color: #3c4043; }}
        .tw-text {{ font-size: 12px; font-weight: 600; margin-top: 4px; }}
        .imp-text {{ font-size: 11px; color: var(--blue); }}
        .opp-highlight {{ background-color: #e6f4ea; }}
        .q-text {{ font-weight: 500; color: #1a0dab; }}
        @media (max-width: 600px) {{
            th {{ display: none; }}
            td {{ display: block; padding: 10px 16px; border: none; text-align: right; }}
            td:before {{ content: attr(data-label); float: left; font-size: 12px; color: #70757a; font-weight: 600; }}
            tr {{ display: block; border-bottom: 8px solid var(--bg); }}
            td[data-label="標的"], td[data-label="預測市場"] {{ text-align: left; background: #f8f9fa; }}
            td[data-label="標的"]:before, td[data-label="預測市場"]:before {{ content: ""; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-top"><div style="font-weight:700; color:var(--blue);">OPENCLAW PRO</div><div style="font-size:12px; color:#70757a;">更新時間: {updated_at}</div></div>
        <div class="tabs"><div class="tab" onclick="sw(0)">📈 美股台股</div><div class="tab active" onclick="sw(1)">🔮 POLYMARKET 套利</div></div>
    </div>
    <div class="container">
        <div id="t0" class="tab-content"><div class="card"><table>
            <thead><tr><th>標的</th><th class="val">價格</th><th class="val">漲跌</th><th>聯動預測</th></tr></thead>
            <tbody>{stock_html}</tbody>
        </table></div></div>
        <div id="t1" class="tab-content active"><div class="card"><table>
            <thead><tr><th>預測市場</th><th class="val">Yes / No Ask</th><th class="val">總價</th><th class="val">獲利 (Edge)</th><th class="val">成交量</th></tr></thead>
            <tbody>{poly_html}</tbody>
        </table></div></div>
    </div>
    <script>function sw(idx){{document.querySelectorAll('.tab').forEach((t, i) => {{t.classList.toggle('active', i === idx);document.getElementById('t'+i).classList.toggle('active', i === idx);}});}}</script>
</body>
</html>'''
    with open('daily_stock_summary/frontend/combined.html', 'w') as f: f.write(html)
    print("Dashboard Update Complete.")

if __name__ == "__main__": generate_dashboard()
