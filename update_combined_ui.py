import yfinance as yf
import time
import os
import requests
import json
import concurrent.futures
import functools

# 全域快取，避免重複查詢相同的名稱
@functools.lru_cache(maxsize=200)
def search_tw_ticker(name):
    """透過 Yahoo Finance API 搜尋台股代碼"""
    try:
        # 手動映射與修正（針對搜尋不穩定的重要個股）
        overrides = {
            '台積電': '2330.TW', '鴻海': '2317.TW', '廣達': '2382.TW', 
            '技嘉': '2376.TW', '世芯-KY': '3661.TW', '大立光': '3008.TW', 
            '貿聯-KY': '3665.TW', '廣達電腦': '2382.TW'
        }
        if name in overrides: return overrides[name]
        
        # 嘗試搜尋代碼
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
    print("Fetching Polymarket Gamma API...")
    try:
        # 使用更寬鬆的條件確保一定能抓到資料
        url = "https://gamma-api.polymarket.com/markets?closed=false&limit=40&order=volume24hrClob&ascending=false"
        resp = requests.get(url, timeout=10)
        markets = resp.json()
        print(f"Gamma API returned {len(markets)} markets")
        
        results = []
        
        def process_market(m):
            try:
                # 兼容不同格式的 token IDs
                token_ids_raw = m.get('clobTokenIds')
                if not token_ids_raw: return None
                
                clob_ids = json.loads(token_ids_raw)
                if len(clob_ids) < 2: return None
                
                # 同時獲取 Yes 和 No 的即時 Ask
                yes_ask = get_clob_price(clob_ids[0])
                no_ask = get_clob_price(clob_ids[1])
                
                if yes_ask and no_ask:
                    bundle = yes_ask + no_ask
                    edge = (1.0 - bundle) * 100
                    return {
                        'title': m.get('question', m.get('title', 'Unknown')),
                        'slug': m.get('slug', ''),
                        'yes': f"{yes_ask:.3f}",
                        'no': f"{no_ask:.3f}",
                        'bundle': f"{bundle:.3f}",
                        'edge_val': edge,
                        'edge': f"{edge:.2f}%",
                        'vol': f"{float(m.get('volume24hrClob', 0))/1000:.1f}K"
                    }
            except Exception as e:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_market = {executor.submit(process_market, m): m for m in markets}
            for future in concurrent.futures.as_completed(future_to_market):
                res = future.result()
                if res: results.append(res)
        
        print(f"Processed {len(results)} valid markets")
        return results
    except Exception as e:
        print(f"Polymarket fetch error: {e}")
        return []

def generate_dashboard():
    print("Starting Dashboard Update...")
    updated_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    
    # 獲取即時數據
    stocks = fetch_stock_data()
    raw_poly = fetch_polymarket_realtime()
    
    # 1. 篩選有套利機會的項目 (Edge >= 1.0 且合理，排除總價 > 1 的異常情況)
    # 總價 > 1 代表兩邊買起來成本超過 1 元，不可能套利；小於 1% 的微小套利空間也排除以減少雜訊
    arbitrage_opps = [m for m in raw_poly if 1.0 <= m['edge_val'] < 50 and float(m['bundle']) <= 1.0]
    arbitrage_opps.sort(key=lambda x: x['edge_val'], reverse=True)
    
    # 2. 篩選討論度最高 (成交量最高) 的熱門項目
    # 同樣排除總價 > 1 的不合理數據，避免誤導
    def get_vol_val(v_str):
        try:
            return float(v_str.replace('K',''))
        except:
            return 0.0

    filtered_hot = [m for m in raw_poly if m['edge_val'] > -50 and float(m['bundle']) <= 1.0]
    hot_markets = sorted(filtered_hot, key=lambda x: get_vol_val(x['vol']), reverse=True)
    # 確保 hot_markets 有值，如果篩選後是空的，就直接用 raw_poly
    if not hot_markets and raw_poly:
        hot_markets = sorted(raw_poly, key=lambda x: get_vol_val(x['vol']), reverse=True)
    
    hot_markets = hot_markets[:10]

    poly_html = ''
    
    # 打印調試資訊
    print(f"Total Raw Markets: {len(raw_poly)}")
    print(f"Arbitrage Opps: {len(arbitrage_opps)}")
    print(f"Hot Markets Count: {len(hot_markets)}")

    if not arbitrage_opps:
        poly_html += '<tr><td colspan="5" style="text-align:center; background: #fff3e0; color: #e65100; font-size: 13px; font-weight: 600; padding: 10px;">⚠️ 目前監測中：暫無即時套利空間 (Edge > 0)</td></tr>'
        poly_html += '<tr><td colspan="5" style="background: #f8f9fa; font-size: 12px; font-weight: 700; padding: 8px 12px; border-bottom: 1px solid var(--border);">🔥 熱門市場 (成交量 Top 10)</td></tr>'
        if not hot_markets:
            poly_html += '<tr><td colspan="5" style="text-align:center; padding: 20px; color: #999;">(暫無熱門市場數據)</td></tr>'
        else:
            for m in hot_markets:
                link = f"https://polymarket.com/market/{m['slug']}" if m['slug'] else "#"
                poly_html += f'''
                <tr>
                    <td data-label="預測市場"><div class="q-text"><a href="{link}" target="_blank" style="text-decoration:none; color:inherit;">{m['title']} 🔗</a></div></td>
                    <td data-label="Yes / No" class="mono val">{m['yes']} / {m['no']}</td>
                    <td data-label="總價" class="mono val">{m['bundle']}</td>
                    <td data-label="獲利 (Edge)" class="mono val"><b class="{'text-green' if m['edge_val']>0 else ''}">{m['edge']}</b></td>
                    <td data-label="成交量" class="val">{m['vol']}</td>
                </tr>'''
    else:
        # 有套利機會時
        for m in arbitrage_opps:
            link = f"https://polymarket.com/market/{m['slug']}" if m['slug'] else "#"
            poly_html += f'''
            <tr class="opp-highlight">
                <td data-label="預測市場"><div class="q-text"><a href="{link}" target="_blank" style="text-decoration:none; color:inherit; font-weight:700;">{m['title']} 🚀</a></div></td>
                <td data-label="Yes / No" class="mono val">{m['yes']} / {m['no']}</td>
                <td data-label="總價" class="mono val">{m['bundle']}</td>
                <td data-label="獲利 (Edge)" class="mono val"><b class="text-green">{m['edge']}</b></td>
                <td data-label="成交量" class="val">{m['vol']}</td>
            </tr>'''
        # 即使有套利，下方也附上熱門市場參考
        if hot_markets:
            poly_html += '<tr><td colspan="5" style="background: #f8f9fa; font-size: 12px; font-weight: 700; padding: 8px 12px; border-top: 2px solid var(--border);">🔥 熱門市場 (成交量參考)</td></tr>'
            for m in hot_markets[:5]:
                link = f"https://polymarket.com/market/{m['slug']}" if m['slug'] else "#"
                poly_html += f'''
                <tr>
                    <td data-label="預測市場"><div class="q-text"><a href="{link}" target="_blank" style="text-decoration:none; color:inherit;">{m['title']} 🔗</a></div></td>
                    <td data-label="Yes / No" class="mono val">{m['yes']} / {m['no']}</td>
                    <td data-label="總價" class="mono val">{m['bundle']}</td>
                    <td data-label="獲利 (Edge)" class="mono val">{m['edge']}</td>
                    <td data-label="成交量" class="val">{m['vol']}</td>
                </tr>'''
    tw_stats = {}
    for s in stocks:
        pred_type = s['pred'] # '看漲', '看跌', '盤整'
        tw_stocks = [x.strip() for x in s['tw'].replace('、', ',').split(',')]
        for ts in tw_stocks:
            if not ts: continue
            if ts not in tw_stats:
                tw_stats[ts] = {'bull': 0, 'bear': 0, 'neutral': 0}
            if pred_type == '看漲': tw_stats[ts]['bull'] += 1
            elif pred_type == '看跌': tw_stats[ts]['bear'] += 1
            else: tw_stats[ts]['neutral'] += 1
    
    tw_html = ''
    # 依看漲次數排序
    sorted_tw = sorted(tw_stats.items(), key=lambda x: (x[1]['bull'], -x[1]['bear']), reverse=True)
    
    # 建立搜尋任務
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        names = [ts for ts, _ in sorted_tw]
        ticker_results = list(executor.map(search_tw_ticker, names))
    
    tw_ticker_map = dict(zip(names, ticker_results))

    # 統計準確度
    total_forecasts = 0
    correct_forecasts = 0

    for ts, counts in sorted_tw:
        price_now = "-"
        price_prev = "-"
        price_now_val = 0
        price_prev_val = 0
        ticker = tw_ticker_map.get(ts)
        if ticker:
            try:
                t_data = yf.Ticker(ticker)
                hist = t_data.history(period="5d")
                if len(hist) >= 2:
                    price_prev_val = hist['Close'].iloc[-2]
                    price_now_val = hist['Close'].iloc[-1]
                    price_prev = f"${price_prev_val:.2f}"
                    price_now = f"${price_now_val:.2f}"
            except: pass

        # 判斷情緒與準確度
        sentiment = '中性'
        if counts['bull'] > counts['bear']: sentiment = '偏多'
        elif counts['bear'] > counts['bull']: sentiment = '偏空'
        
        accuracy_icon = ""
        if price_now_val > 0 and price_prev_val > 0 and sentiment != '中性':
            total_forecasts += 1
            is_correct = False
            if sentiment == '偏多' and price_now_val > price_prev_val: is_correct = True
            elif sentiment == '偏空' and price_now_val < price_prev_val: is_correct = True
            
            if is_correct:
                correct_forecasts += 1
                accuracy_icon = "✅"
            else:
                accuracy_icon = "❌"

        score_cls = 'text-green' if counts['bull'] > counts['bear'] else ('text-red' if counts['bear'] > counts['bull'] else '')
        tw_html += f'''
        <tr>
            <td data-label="台股標的"><b>{ts} {accuracy_icon}</b></td>
            <td data-label="價格歷史" class="mono val">
                <div style="font-size: 11px; color: #70757a; border-bottom: 1px solid #eee; padding-bottom: 2px;">昨收: {price_prev}</div>
                <div style="font-size: 14px; font-weight: 700; padding-top: 2px;">現價: {price_now}</div>
            </td>
            <td data-label="看漲" class="mono val text-green">{counts['bull']}</td>
            <td data-label="看跌" class="mono val text-red">{counts['bear']}</td>
            <td data-label="綜合情緒" class="val"><b class="{score_cls}">{sentiment}</b></td>
        </tr>'''

    acc_rate = (correct_forecasts / total_forecasts * 100) if total_forecasts > 0 else 0
    
    # 保存歷史紀錄
    history = []
    try:
        log_file = 'prediction_history.json'
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
                if content: history = json.loads(content)
        
        # 避免同日重複紀錄（以日期為 key，更新當日最新的準確率）
        today_str = time.strftime('%Y-%m-%d', time.localtime())
        history = [h for h in history if h.get('date') != today_str]
        
        history.append({
            'date': today_str,
            'time': updated_at,
            'accuracy': round(acc_rate, 1),
            'correct': correct_forecasts,
            'total': total_forecasts
        })
        # 保留最近 60 筆
        history = history[-60:]
        with open(log_file, 'w') as f: json.dump(history, f, indent=2)
    except: pass

    # 生成歷史記錄 HTML
    history_rows = ""
    total_correct_all = sum(h['correct'] for h in history)
    total_forecasts_all = sum(h['total'] for h in history)
    
    for h in reversed(history):
        history_rows += f"<tr><td>{h['date']}</td><td class='val'>{h['accuracy']}%</td><td class='val'>{h['correct']}/{h['total']}</td></tr>"

    accuracy_html = f'''
    <div class="card" style="padding: 16px; background: #e8f0fe; border-left: 5px solid var(--blue); margin-bottom: 20px; position: relative;">
        <div style="font-size: 12px; color: #5f6368; font-weight: 600;">今日預測準確度分析</div>
        <div style="display: flex; align-items: baseline; gap: 10px; margin-top: 8px;">
            <span style="font-size: 32px; font-weight: 800; color: var(--blue);">{acc_rate:.1f}%</span>
            <span style="font-size: 14px; color: #70757a;">({correct_forecasts} / {total_forecasts} 命中)</span>
        </div>
        <div style="font-size: 11px; color: #70757a; margin-top: 4px;">* 隨股價變動實時計算</div>
        <div onclick="toggleHistory()" style="position: absolute; right: 16px; top: 16px; cursor: pointer; background: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 1px solid #ddd;">ℹ️</div>
        
        <div id="history-panel" style="display:none; margin-top: 16px; border-top: 1px solid #d2e3fc; padding-top: 16px;">
            <div style="background: white; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                <div style="font-size: 12px; font-weight: 700; margin-bottom: 8px;">累積預測對決 (PK)</div>
                <div style="height: 24px; background: #fce8e6; border-radius: 12px; overflow: hidden; display: flex; position: relative;">
                    <div style="width: {(total_correct_all/total_forecasts_all*100) if total_forecasts_all>0 else 0}%; background: #e6f4ea; height: 100%; display: flex; align-items: center; padding-left: 10px; color: #137333; font-size: 11px; font-weight: 700; transition: width 0.5s;">正確: {total_correct_all}</div>
                    <div style="flex: 1; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; color: #d93025; font-size: 11px; font-weight: 700;">錯誤: {total_forecasts_all - total_correct_all}</div>
                </div>
            </div>
            <table style="width: 100%; font-size: 12px;">
                <thead><tr style="background: transparent;"><th style="padding: 4px 0;">日期</th><th class="val" style="padding: 4px 0;">準確率</th><th class="val" style="padding: 4px 0;">命中</th></tr></thead>
                <tbody>{history_rows}</tbody>
            </table>
        </div>
    </div>
    <script>
        function toggleHistory() {{
            const p = document.getElementById('history-panel');
            p.style.display = p.style.display === 'none' ? 'block' : 'none';
        }}
    </script>
    '''

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
    if not arbitrage_opps:
        poly_html += '<tr><td colspan="5" style="text-align:center; background: #fff3e0; color: #e65100; font-size: 13px; font-weight: 600; padding: 10px;">⚠️ 目前監測中：暫無即時套利空間 (Edge >= 1%)</td></tr>'
        poly_html += '<tr><td colspan="5" style="background: #f8f9fa; font-size: 12px; font-weight: 700; padding: 8px 12px; border-bottom: 1px solid var(--border);">🔥 熱門市場 (成交量 Top 10)</td></tr>'
        if not hot_markets:
            poly_html += '<tr><td colspan="5" style="text-align:center; padding: 20px; color: #999;">(暫無熱門市場數據)</td></tr>'
        else:
            for m in hot_markets:
                link = f"https://polymarket.com/market/{m['slug']}" if m['slug'] else "#"
                # 只有 Edge >= 1% 才顯示綠色，否則顯示灰色
                edge_style = 'class="text-green"' if m['edge_val'] >= 1.0 else 'style="color:#999; font-weight:400;"'
                poly_html += f'''
                <tr>
                    <td data-label="預測市場"><div class="q-text"><a href="{link}" target="_blank" style="text-decoration:none; color:#1a0dab; font-weight:500;">{m['title']} 🔗</a></div></td>
                    <td data-label="Yes / No" class="mono val">{m['yes']} / {m['no']}</td>
                    <td data-label="總價" class="mono val">{m['bundle']}</td>
                    <td data-label="獲利 (Edge)" class="mono val"><b {edge_style}>{m['edge']}</b></td>
                    <td data-label="成交量" class="val">{m['vol']}</td>
                </tr>'''
    else:
        # 有套利機會時
        for m in arbitrage_opps:
            link = f"https://polymarket.com/market/{m['slug']}" if m['slug'] else "#"
            poly_html += f'''
            <tr class="opp-highlight">
                <td data-label="預測市場"><div class="q-text"><a href="{link}" target="_blank" style="text-decoration:none; color:#1a0dab; font-weight:700;">{m['title']} 🚀</a></div></td>
                <td data-label="Yes / No" class="mono val">{m['yes']} / {m['no']}</td>
                <td data-label="總價" class="mono val">{m['bundle']}</td>
                <td data-label="獲利 (Edge)" class="mono val"><b class="text-green">{m['edge']}</b></td>
                <td data-label="成交量" class="val">{m['vol']}</td>
            </tr>'''
        # 即使有套利，下方也附上熱門市場參考
        if hot_markets:
            poly_html += '<tr><td colspan="5" style="background: #f8f9fa; font-size: 12px; font-weight: 700; padding: 8px 12px; border-top: 2px solid var(--border);">🔥 熱門市場 (成交量參考)</td></tr>'
            for m in hot_markets[:5]:
                link = f"https://polymarket.com/market/{m['slug']}" if m['slug'] else "#"
                edge_style = 'class="text-green"' if m['edge_val'] >= 1.0 else 'style="color:#999; font-weight:400;"'
                poly_html += f'''
                <tr>
                    <td data-label="預測市場"><div class="q-text"><a href="{link}" target="_blank" style="text-decoration:none; color:#1a0dab; font-weight:500;">{m['title']} 🔗</a></div></td>
                    <td data-label="Yes / No" class="mono val">{m['yes']} / {m['no']}</td>
                    <td data-label="總價" class="mono val">{m['bundle']}</td>
                    <td data-label="獲利 (Edge)" class="mono val"><b {edge_style}>{m['edge']}</b></td>
                    <td data-label="成交量" class="val">{m['vol']}</td>
                </tr>'''

    # --- 前端實時報價腳本 (JS) ---
    realtime_script = '''
    <script>
        // 定義需要監控的標的清單
        const STOCKS = {
            "US": ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "SMCI"],
            "TW": ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "2308.TW", "3008.TW", "2303.TW", "2412.TW"]
        };

        async function updatePrices() {
            try {
                // 使用 Yahoo Finance Query API (前端可用的 CORS proxy 或公開介面)
                // 為了穩定性，這裡使用一個輕量化的彙整邏輯
                for (const symbol of [...STOCKS.US, ...STOCKS.TW]) {
                    // 模擬實時抓取邏輯 (實際部署時可對接特定的 Finance API)
                    // 這裡先實作 UI 閃爍與動態更新的框架
                    const cells = document.querySelectorAll(`[data-symbol="${symbol}"]`);
                    cells.forEach(cell => {
                        // 這裡未來可對接即時 API 數據
                        // cell.classList.add('updating');
                        // setTimeout(() => cell.classList.remove('updating'), 500);
                    });
                }
            } catch (e) { console.error("Price update failed", e); }
        }
        
        // 每 15 秒更新一次前端報價 (不經過 GitHub)
        // setInterval(updatePrices, 15000);
    </script>
    <style>
        .updating { background-color: rgba(26, 115, 232, 0.1); transition: background 0.3s; }
    </style>
    '''

    html = f'''<!doctype html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>JoeClowAI - 實時監控</title>
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
<body onload="checkReload()">
    {realtime_script}
    <script>
        function sw(idx){{
            document.querySelectorAll('.tab').forEach((t, i) => {{
                t.classList.toggle('active', i === idx);
                document.getElementById('t'+i).classList.toggle('active', i === idx);
            }});
            localStorage.setItem('activeTab', idx);
        }}
        function checkReload() {{
            const savedTab = localStorage.getItem('activeTab');
            if (savedTab !== null) sw(parseInt(savedTab));
            // 每 60 秒刷新一次 (後台同步數據)
            setInterval(() => {{ 
                const url = new URL(window.location.href);
                url.searchParams.set('t', Date.now());
                window.location.href = url.href;
            }}, 60000);
        }}
    </script>
    <div class="header">
        <div class="header-top"><div style="font-weight:700; color:var(--blue);">JoeClowAI</div><div style="font-size:12px; color:#70757a;">更新時間: {updated_at}</div></div>
        <div class="tabs">
            <div class="tab" onclick="sw(0)">🔮 套利</div>
            <div class="tab" onclick="sw(1)">📈 美股</div>
            <div class="tab" onclick="sw(2)">🇹🇼 台股預測</div>
        </div>
    </div>
    <div class="container">
        <!-- Tab 0: Polymarket -->
        <div id="t0" class="tab-content active"><div class="card"><table>
            <thead><tr><th>預測市場</th><th class="val">Yes / No Ask</th><th class="val">總價</th><th class="val">獲利 (Edge)</th><th class="val">成交量</th></tr></thead>
            <tbody>{poly_html}</tbody>
        </table></div></div>
        
        <!-- Tab 1: US Stocks -->
        <div id="t1" class="tab-content"><div class="card"><table>
            <thead><tr><th>標的</th><th class="val">價格</th><th class="val">漲跌</th><th>聯動預測</th></tr></thead>
            <tbody>{stock_html}</tbody>
        </table></div></div>

        <!-- Tab 2: TW Forecast -->
        <div id="t2" class="tab-content">
            {accuracy_html}
            <div class="card"><table>
                <thead><tr><th>台股標的</th><th class="val">價格對比 (昨收/現價)</th><th class="val">看漲</th><th class="val">看跌</th><th class="val">綜合情緒</th></tr></thead>
                <tbody>{tw_html}</tbody>
            </table></div>
        </div>
    </div>
    <script>function sw(idx){{
        document.querySelectorAll('.tab').forEach((t, i) => {{
            t.classList.toggle('active', i === idx);
            document.getElementById('t'+i).classList.toggle('active', i === idx);
        }});
        localStorage.setItem('activeTab', idx);
    }}</script>
</body>
</html>'''
    with open('daily_stock_summary/frontend/combined.html', 'w') as f: f.write(html)
    print("Dashboard Update Complete.")

if __name__ == "__main__": generate_dashboard()
