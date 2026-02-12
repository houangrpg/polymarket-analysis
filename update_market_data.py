import sqlite3
import yfinance as yf
import requests
import holidays
import pytz
from datetime import datetime, time
import subprocess
import os
import json
from update_html import generate_html

# Configuration
DB_PATH = 'joeclaw.db'
TICKERS = {
    '^GSPC': 'S&P 500',
    '^IXIC': 'Nasdaq',
    '2330.TW': 'TSMC',
    'NVDA': 'NVIDIA',
    'AAPL': 'Apple',
    'BTC-USD': 'Bitcoin'
}

# Market Hours (Asia/Taipei)
TAIPEI_TZ = pytz.timezone('Asia/Taipei')
US_TZ = pytz.timezone('America/New_York')

def is_market_open():
    """Check if either Taiwan or US markets are currently open."""
    now_tp = datetime.now(TAIPEI_TZ)
    
    # Taiwan Market: Mon-Fri 09:00 - 13:30
    tw_holidays = holidays.Taiwan()
    if now_tp.weekday() < 5 and now_tp.date() not in tw_holidays:
        if time(9, 0) <= now_tp.time() <= time(13, 30):
            return True

    # US Market: Mon-Fri 09:30 - 16:00 (New York Time)
    now_ny = datetime.now(US_TZ)
    us_holidays = holidays.UnitedStates()
    if now_ny.weekday() < 5 and now_ny.date() not in us_holidays:
        if time(9, 30) <= now_ny.time() <= time(16, 0):
            return True

    return False

def get_category(ticker):
    if '.TW' in ticker: return 'Taiwan Stocks'
    if ticker in ['^GSPC', '^IXIC']: return 'US Stocks'
    if ticker == 'BTC-USD': return 'Crypto'
    return 'Tech Stocks'

def get_yfinance_data():
    data = []
    for ticker, name in TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                change_str = "0.00%"
                if len(hist) > 1:
                    prev = hist['Close'].iloc[-2]
                    change = (price - prev) / prev * 100
                    change_str = f"{change:+.2f}%"
                
                data.append({
                    'category': get_category(ticker),
                    'name': name,
                    'price': f"${price:,.2f}" if ticker != '^GSPC' and ticker != '^IXIC' else f"{price:,.2f}",
                    'change': change_str
                })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
    return data

def get_polymarket_data():
    data = []
    queries = ["Fed rate cut", "Bitcoin price", "Taiwan"]
    for query in queries:
        try:
            url = f"https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=3&query={query}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for m in resp.json():
                    try:
                        # Robust outcome price parsing
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        outcomes = json.loads(m.get('outcomes', '[]'))
                        
                        if not prices or not outcomes: continue
                        
                        # Find 'Yes' or the first outcome
                        target_idx = 0
                        if 'Yes' in outcomes:
                            target_idx = outcomes.index('Yes')
                        
                        prob = float(prices[target_idx]) * 100
                        change_val = m.get('oneDayPriceChange', 0) * 100
                        
                        data.append({
                            'category': 'Polymarket',
                            'name': m['question'],
                            'price': f"{prob:.1f}%",
                            'change': f"{change_val:+.1f}%"
                        })
                    except:
                        continue
        except Exception as e:
            print(f"Polymarket error for {query}: {e}")
    return data

def update_db(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    changed = False
    
    for item in data:
        cursor.execute("SELECT price, change FROM market_data WHERE name = ?", (item['name'],))
        row = cursor.fetchone()
        if not row or row[0] != item['price'] or row[1] != item['change']:
            changed = True
            cursor.execute("""
                INSERT OR REPLACE INTO market_data (category, name, price, change)
                VALUES (?, ?, ?, ?)
            """, (item['category'], item['name'], item['price'], item['change']))
    
    conn.commit()
    conn.close()
    return changed

def git_sync():
    try:
        # Add DB and generated index.html
        subprocess.run(["git", "add", "joeclaw.db", "index.html"], check=True)
        # Check if there are changes
        status = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if status.returncode != 0:
            subprocess.run(["git", "commit", "-m", f"Site Auto-Update: {datetime.now(TAIPEI_TZ).strftime('%Y-%m-%d %H:%M')}"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Successfully synced to GitHub.")
        else:
            print("No changes to sync.")
    except Exception as e:
        print(f"Git sync error: {e}")

def main():
    is_manual = os.getenv("MANUAL_RUN") == "1"
    if not is_manual and not is_market_open():
        print("Markets closed. Skipping update.")
        return

    print(f"Updating JoeClawSite data at {datetime.now(TAIPEI_TZ).strftime('%Y-%m-%d %H:%M:%S')}...")
    
    all_data = get_yfinance_data() + get_polymarket_data()
    
    if all_data:
        if update_db(all_data):
            print("DB updated. Re-generating HTML...")
            generate_html()
            git_sync()
        else:
            print("Data fetch complete. No value changes detected.")
    else:
        print("Failed to fetch any data.")

if __name__ == "__main__":
    main()
