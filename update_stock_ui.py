import yfinance as yf
import time
import os

def fetch_stock_data(tickers):
    data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            # 獲取最新價格和資訊
            info = stock.info
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            prev_close = info.get('previousClose')
            
            if current_price and prev_close:
                change_pct = ((current_price - prev_close) / prev_close) * 100
                change_str = f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%"
            else:
                change_str = "N/A"
            
            # 簡單的情緒判斷 (之後可以接入 LLM)
            sentiment = "Bullish" if change_pct > 0 else "Neutral"
            if change_pct > 3: sentiment = "Strong Bullish"
            if change_pct < -2: sentiment = "Bearish"

            data.append({
                'symbol': ticker,
                'name': info.get('longName', ticker),
                'price': current_price,
                'change': change_str,
                'sentiment': sentiment,
                'vol': f"{info.get('regularMarketVolume', 0) / 1e6:.1f}M"
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
    return data

def generate_stock_dashboard():
    updated_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    
    # 抓取真實數據
    target_stocks = ['TSLA', 'AAPL', 'NVDA', 'MSFT', 'AMZN', 'GOOGL', 'META']
    stocks = fetch_stock_data(target_stocks)
    
    rows_html = ''
    for s in stocks:
        change_class = 'text-green' if '+' in s['change'] else 'text-red'
        sentiment_class = 'badge-bull' if 'Bullish' in s['sentiment'] else 'badge-neutral'
        if 'Bearish' in s['sentiment']: sentiment_class = 'badge-red'
        
        rows_html += f'''
      <tr>
        <td>
          <div class="market-cell">
            <div class="m-img-placeholder">{s['symbol'][0]}</div>
            <div class="q-wrap">
              <div class="question-link">{s['name']}</div>
              <div class="slug-text">{s['symbol']}</div>
            </div>
          </div>
        </td>
        <td class="mono val highlight" style="font-size: 24px; font-weight: 900;">${s['price']:.2f}</td>
        <td class="mono val {change_class}" style="font-size: 20px; font-weight: bold;">{s['change']}</td>
        <td class="val"><span class="badge {sentiment_class}">{s['sentiment']}</span></td>
        <td class="mono val">{s['vol']}</td>
      </tr>'''

    html = f'''<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>美股即時分析儀表板</title>
  <style>
    :root {{
      --pm-blue: #1a73e8;
      --bg-gray: #f8f9fa;
      --text-main: #202124;
      --text-muted: #5f6368;
      --border-color: #dadce0;
      --up-green: #137333;
      --down-red: #d93025;
    }}
    body {{ 
      font-family: "Google Sans", Roboto, Arial, sans-serif; 
      margin: 0; background-color: var(--bg-gray); color: var(--text-main); line-height: 1.5;
    }}
    .header {{ background: white; border-bottom: 1px solid var(--border-color); padding: 16px 24px; position: sticky; top: 0; z-index: 100; }}
    .header-content {{ max-width: 1000px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }}
    h1 {{ margin: 0; font-size: 22px; font-weight: 500; display: flex; align-items: center; gap: 10px; }}
    .container {{ max-width: 1000px; margin: 32px auto; padding: 0 16px; }}
    .card {{ background: white; border-radius: 8px; border: 1px solid var(--border-color); overflow: hidden; }}
    .meta-bar {{ padding: 12px 20px; background: #fafafa; border-bottom: 1px solid var(--border-color); font-size: 13px; color: var(--text-muted); }}
    
    table {{ border-collapse: collapse; width: 100%; }}
    th {{ background: #f8f9fa; padding: 12px 16px; text-align: left; font-size: 11px; font-weight: 500; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border-color); }}
    td {{ padding: 16px; border-bottom: 1px solid var(--border-color); vertical-align: middle; }}
    
    .market-cell {{ display: flex; align-items: center; gap: 12px; }}
    .m-img-placeholder {{ width: 32px; height: 32px; border-radius: 4px; background: #e8f0fe; color: #1a73e8; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }}
    .question-link {{ color: var(--text-main); font-weight: 500; font-size: 15px; }}
    .slug-text {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}
    
    .mono {{ font-family: "Roboto Mono", monospace; font-size: 14px; }}
    .val {{ text-align: right; }}
    .highlight {{ font-weight: 500; color: #1a1a1a; }}
    .text-green {{ color: var(--up-green); font-weight: 500; }}
    .text-red {{ color: var(--down-red); font-weight: 500; }}
    
    .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }}
    .badge-bull {{ background: #e6f4ea; color: #137333; }}
    .badge-neutral {{ background: #f1f3f4; color: #3c4043; }}
    .badge-red {{ background: #fce8e6; color: #d93025; }}
    
    tr:hover {{ background-color: #f8f9fa; }}
  </style>
</head>
<body>
  <div class="header">
    <div class="header-content">
      <h1>📈 美股即時分析儀表板</h1>
      <div style="font-size: 14px; color: var(--text-muted);">Real-time Insights</div>
    </div>
  </div>

  <div class="container">
    <div class="card">
      <div class="meta-bar">
        <span>🕒 最後抓取時間: {updated_at}</span>
        <span style="margin-left: 20px;">📊 數據來源: Yahoo Finance API</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>個股名稱</th>
            <th class="val">最新成交價</th>
            <th class="val">漲跌幅</th>
            <th class="val">自動情緒</th>
            <th class="val">成交量</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>'''
    output_path = 'daily_stock_summary/frontend/index.html'
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"Successfully generated dashboard at {output_path}")

if __name__ == "__main__":
    generate_stock_dashboard()
