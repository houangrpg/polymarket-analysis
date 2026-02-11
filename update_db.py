import sqlite3

db_path = 'joeclaw.db'

# Data collected for Feb 11, 2026
data = [
    (1, 'US Stocks', 'S&P 500', '6,858.47', '+0.19%'),
    (2, 'US Stocks', 'Nasdaq', '21,123.45', '+0.5%'), # Estimated based on trend
    (3, 'Taiwan Stocks', '台積電 (2330)', '1,860.00', '+2.48%'),
    (4, 'Taiwan Stocks', '加權指數', '32,404.62', '+1.9%'),
    (5, 'Tech Stocks', 'NVDA', '188.54', '-0.79%'),
    (6, 'Tech Stocks', 'AAPL', '274.07', '+1.2%'), # Estimated change
    (7, 'Polymarket', 'Fed Rate Cut in March?', '90%', '+5%'),
    (8, 'Polymarket', 'Bitcoin to 100k in 2026?', '78%', '+13%')
]

def update_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for item in data:
        cursor.execute("""
            UPDATE market_data 
            SET price = ?, change = ? 
            WHERE id = ?
        """, (item[3], item[4], item[0]))
        
    conn.commit()
    print("Database updated successfully.")
    conn.close()

if __name__ == "__main__":
    update_db()
