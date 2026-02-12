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

    # Fetch promotions so we can inject them into the client-side JS
    cursor.execute("SELECT platform, name, deal_price, original_price, url FROM promotions")
    promo_rows = cursor.fetchall()

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
                <div class=\"market-item\">\n                    <div class=\"asset-info\">\n                        <span class=\"asset-name\">{item['name']}</span>\n                        <span class=\"asset-price\">{item['price']}</span>\n                    </div>\n                    <span class=\"asset-change {change_class}\">{item['change']}</span>\n                </div>"""

        cards_html += f"""
        <section class=\"card\">\n            <h2>{cat} <span>{icon}</span></h2>\n            <div class=\"market-list\">\n                {items_html}\n            </div>\n        </section>"""

    # Build promotions JS array (client-side)
    deals_js_items = []
    for platform, name, deal_price, original_price, url in promo_rows:
        # escape single quotes
        name_esc = name.replace("'", "\\'") if name else ''
        platform_esc = platform.replace("'", "\\'") if platform else ''
        url_esc = url.replace("'", "\\'") if url else ''
        deals_js_items.append("{" + f" platform: '{platform_esc}', name: '{name_esc}', price: '{deal_price}', original: '{original_price}', url: '{url_esc}' " + "}")

    deals_js = "const deals = [\n" + ",\n".join(deals_js_items) + "\n];"

    # Read original HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Replace the <main> content
    start_tag = "<main>"
    end_tag = "</main>"
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    new_html = html_content[:start_idx] + cards_html + html_content[end_idx:]

    # Replace the static deals array in the JS refreshPromotions() function
    marker_start = 'const deals = ['
    if marker_start in new_html:
        s_idx = new_html.find(marker_start)
        e_idx = new_html.find('];', s_idx)
        if e_idx != -1:
            e_idx += 2  # include the closing ];
            new_html = new_html[:s_idx] + deals_js + new_html[e_idx:]

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print("index.html updated successfully (market cards + promotions injected).")

if __name__ == "__main__":
    generate_html()
