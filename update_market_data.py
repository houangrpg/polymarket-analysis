import sqlite3
import yfinance as yf
import requests
import holidays
import pytz
from datetime import datetime, time
import subprocess
import os
import json

# Configuration
DB_PATH = 'joeclaw.db'
TICKERS = {
    '^GSPC': 'S&P 500',
    '^IXIC': 'Nasdaq',
    '2330.TW': 'TSMC',
    'NVDA': 'NVIDIA',
    'AAPL': 'Apple'
}

# Market Hours (Asia/Taipei)
TAIPEI_TZ = pytz.timezone('Asia/Taipei')
US_TZ = pytz.timezone('America/New_York')

def is_market_open():
    now = datetime.now(TAIPEI_TZ)
    weekday = now.weekday()
    
    # Weekends (Taipei)
    if weekday >= 5:
        # Check if US market is still open (Fri US time = Sat early morning Taipei time)
        if weekday == 5 and now.time() < time(5, 0): # US market closes at 04:00 Taipei time
            pass 
        else:
            return False

    # Taiwan Market Hours: 09:00 - 13:30
    tw_holidays = holidays.Taiwan()
    if now.date() in tw_holidays:
        pass # Handle US check below
    else:
        tw_start = time(9, 0)
        tw_end = time(13, 30)
        if tw_start <= now.time() <= tw_end:
            return True

    # US Market Hours: 21:30 - 04:00 (Taipei Time)
    us_holidays = holidays.UnitedStates()
    now_us = datetime.now(US_TZ)
    
    if now_us.date() in us_holidays:
        return False
        
    if now_us.weekday() < 5:
        ny_start = time(9, 30)
        ny_end = time(16, 0)
        if ny_start <= now_us.time() <= ny_end:
            return True

    return False

def get_yfinance_data():
    data = []
    for ticker, name in TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                # Try to calculate change if possible
                change_str = "0.00%"
                if len(hist) > 1:
                    prev = hist['Close'].iloc[-2]
                    change = (price - prev) / prev * 100
                    change_str = f"{change:+.2f}%"
                
                data.append({
                    'category': 'Stock',
                    'name': name,
                    'price': f"${price:,.2f}" if '^' not in ticker else f"{price:,.2f}",
                    'change': change_str
                })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
    return data

def get_polymarket_data():
    data = []
    try:
        queries = ["Fed rate cut", "Bitcoin price"]
        for query in queries:
            url = f"https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=3&query={query}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                markets = resp.json()
                for m in markets:
                    if 'outcomes' in m and 'outcomePrices' in m:
                        try:
                            outcomes = json.loads(m['outcomes'])
                            prices = json.loads(m['outcomePrices'])
                            if 'Yes' in outcomes:
                                idx = outcomes.index('Yes')
                                prob = float(prices[idx]) * 100
                                # Calculate "change" from oneDayPriceChange if available
                                change_val = m.get('oneDayPriceChange', 0) * 100
                                data.append({
                                    'category': 'Prediction',
                                    'name': m['question'],
                                    'price': f"{prob:.1f}%",
                                    'change': f"{change_val:+.1f}%"
                                })
                        except:
                            continue
    except Exception as e:
        print(f"Polymarket error: {e}")
    return data

def update_db(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We'll use name as a key for current schema since symbol is missing
    # But for robustness, let's keep the existing structure if possible or wipe and refill
    # The requirement is to update 'market_data' table.
    
    changed = False
    for item in data:
        cursor.execute("SELECT price FROM market_data WHERE name = ?", (item['name'],))
        row = cursor.fetchone()
        if not row or row[0] != item['price']:
            changed = True
            cursor.execute("""
                INSERT OR REPLACE INTO market_data (category, name, price, change)
                VALUES (?, ?, ?, ?)
            """, (item['category'], item['name'], item['price'], item['change']))
    
    conn.commit()
    conn.close()
    return changed

def git_push():
    try:
        subprocess.run(["git", "add", "joeclaw.db"], check=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode != 0:
            subprocess.run(["git", "commit", "-m", f"Auto-update market data: {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Git push successful.")
        else:
            print("No changes to commit.")
    except Exception as e:
        print(f"Git error: {e}")

def main():
    is_manual = os.getenv("MANUAL_RUN") == "1"
    if not is_manual and not is_market_open():
        print("Markets closed. Skipping update.")
        return

    print("Fetching data...")
    yf_list = get_yfinance_data()
    poly_list = get_polymarket_data()
    
    all_data = yf_list + poly_list
    
    if all_data:
        changed = update_db(all_data)
        if changed:
            print(f"Data updated in DB ({len(all_data)} items).")
            git_push()
        else:
            print("No changes detected.")
    else:
        print("No data fetched.")

if __name__ == "__main__":
    main()
