import sqlite3
import os

db_path = 'joeclaw.db'
html_path = 'index.html'

def generate_html():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch all market data
    cursor.execute("SELECT category, name, price, change FROM market_data")
    rows = cursor.fetchall()
    
    # Group data by category
    categories = {}
    for cat, name, price, change in rows:
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            'name': name,
            'price': price,
            'change': change
        })
        
    conn.close()

    # Define icons for categories
    icons = {
        'US Stocks': '🇺🇸',
        'Taiwan Stocks': '🇹🇼',
        'Tech Stocks': '💻',
        'Polymarket': '🎲'
    }

    # Generate the cards HTML
    cards_html = ""
    for cat, items in categories.items():
        icon = icons.get(cat, '📊')
        items_html = ""
        for item in items:
            change_class = "change-up" if "+" in item['change'] else "change-down"
            items_html += f"""
                <div class="market-item">
                    <div class="asset-info">
                        <span class="asset-name">{item['name']}</span>
                        <span class="asset-price">{item['price']}</span>
                    </div>
                    <span class="asset-change {change_class}">{item['change']}</span>
                </div>"""
        
        cards_html += f"""
        <section class="card">
            <h2>{cat} <span>{icon}</span></h2>
            <div class="market-list">
                {items_html}
            </div>
        </section>"""

    # Read original HTML and replace the main content
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Find the <main> block and replace its content
    start_tag = "<main>"
    end_tag = "</main>"
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    
    new_html = html_content[:start_idx] + cards_html + html_content[end_idx:]

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)
        
    print("index.html updated successfully.")

if __name__ == "__main__":
    generate_html()
