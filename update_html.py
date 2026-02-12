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

    # Read news JSON (top-3 per category) and build HTML sections + full pages
    import json
    news_public = os.path.join(os.path.dirname(__file__), 'public', 'news')
    news_sections_html = ""
    for cat, title in [('ai', 'AI 最新'), ('health', '智慧醫療 最新')]:
        json_path = os.path.join(news_public, f"{cat}.json")
        items = []
        try:
            with open(json_path, 'r', encoding='utf-8') as jf:
                items = json.load(jf)
        except Exception:
            items = []
        # build top-3 preview
        preview_html = ''
        for item in items[:3]:
            preview_html += f"""
                <div class=\"market-item\">
                    <div class=\"asset-info\">
                        <span class=\"asset-name\">{item.get('title')}</span>
                        <span class=\"asset-price\">{item.get('source')}</span>
                    </div>
                    <div style=\"width:100%;margin-top:0.5rem;\">{item.get('summary')} <a href=\"{item.get('link')}\" target=\"_blank\">（原文）</a></div>
                </div>"""
        if preview_html:
            news_sections_html += f"""
            <section class=\"card\">
                <h2>{title} <span>📰</span></h2>
                <div class=\"market-list\">{preview_html}</div>
                <div style=\"text-align:right;margin-top:0.5rem;\"><a href=\"news_{cat}.html\">更多{title}</a></div>
            </section>"""
        # build full page for this category
        full_items_html = ''
        for item in items:
            full_items_html += f"""
            <div class=\"market-item\" style=\"flex-direction:column;align-items:flex-start;\">\n                <div style=\"font-weight:700;\">{item.get('title')}</div>\n                <div style=\"color:#94a3b8;font-size:0.9rem;\">{item.get('source')} • {item.get('fetched_at')}</div>\n                <div style=\"margin-top:0.25rem;\">{item.get('summary')} <a href=\"{item.get('link')}\" target=\"_blank\">（原文）</a></div>\n            </div>\n            <hr/>"""
        page_html = f"""
        <!doctype html>
        <html lang=\"zh-TW\">
        <head>
        <meta charset=\"utf-8\">
        <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
        <title>{title} - JoeClawSite</title>
        <style>body{{font-family:Inter,system-ui,sans-serif;background:#020617;color:#f8fafc;padding:2rem}}.market-item{{padding:0.75rem 0}}</style>
        </head>
        <body>
        <h1>{title}</h1>
        <div>
        {full_items_html}
        </div>
        <div style=\"margin-top:1rem\"><a href=\"index.html\">回到首頁</a></div>
        </body>
        </html>
        """
        try:
            with open(os.path.join(os.path.dirname(__file__), f'news_{cat}.html'), 'w', encoding='utf-8') as pf:
                pf.write(page_html)
        except Exception:
            pass

    # Read original HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Replace the <main> content
    start_tag = "<main>"
    end_tag = "</main>"
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    new_html = html_content[:start_idx] + cards_html + news_sections_html + html_content[end_idx:]

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

    print("index.html updated successfully (market cards + promotions injected and news sections generated).")

if __name__ == "__main__":
    generate_html()
