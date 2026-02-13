import sqlite3
import os
import datetime
from zoneinfo import ZoneInfo

db_path = 'joeclaw.db'
html_path = 'index.html'


def is_us_market_open(now_utc=None):
    # US market hours (NYSE/Nasdaq): Mon-Fri 09:30-16:00 America/New_York (ET)
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    try:
        ny = now_utc.astimezone(ZoneInfo('America/New_York'))
    except Exception:
        # fallback: assume not trading
        return False
    if ny.weekday() >= 5:  # Saturday=5 Sunday=6
        return False
    open_time = ny.replace(hour=9, minute=30, second=0, microsecond=0)
    close_time = ny.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_time <= ny <= close_time


def generate_html():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all market data (robust: if table missing, continue with empty market cards)
    rows = []
    try:
        cursor.execute("SELECT category, name, price, change FROM market_data")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Warning: could not fetch market_data: {e}")
        rows = []

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
    promo_rows = []
    try:
        cursor.execute("SELECT platform, name, deal_price, original_price, url, updated_at FROM promotions")
        promo_rows = cursor.fetchall()
    except Exception as e:
        print(f"Warning: could not fetch promotions: {e}")
        promo_rows = []

    conn.close()

    # Determine if US market is open now (used to decide whether to perform live refresh on client)
    trading_now = is_us_market_open()

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
        # If market is closed, add a note to the header
        header_extra = '（非交易時間）' if (not trading_now and 'Stocks' in cat) else ''
        items_html = ""
        for item in items:
            change_text = item['change'] if item.get('change') is not None else ''
            change_class = "change-up" if "+" in change_text else "change-down"
            # Use final price as stored in DB; if market closed, we assume DB contains last close
            items_html += f"""
                <div class=\"market-item\">\n                    <div class=\"asset-info\">\n                        <span class=\"asset-name\">{item['name']}</span>\n                        <span class=\"asset-price\">{item['price']}</span>\n                    </div>\n                    <span class=\"asset-change {change_class}\">{change_text}</span>\n                </div>"""

        cards_html += f"""
        <section class=\"card\">\n            <h2>{cat} {header_extra} <span>{icon}</span></h2>\n            <div class=\"market-list\">\n                {items_html}\n            </div>\n        </section>"""

    # Build promotions JS array (client-side)
    deals_js_items = []
    for row in promo_rows:
        # row may include updated_at at index 5
        platform = row[0] if len(row) > 0 else ''
        name = row[1] if len(row) > 1 else ''
        deal_price = row[2] if len(row) > 2 else ''
        original_price = row[3] if len(row) > 3 else ''
        url = row[4] if len(row) > 4 else ''
        name_esc = (name.replace("'", "\\'") if name else '')
        platform_esc = (platform.replace("'", "\\'") if platform else '')
        url_esc = (url.replace("'", "\\'") if url else '')
        deals_js_items.append("{" + f" platform: '{platform_esc}', name: '{name_esc}', price: '{deal_price}', original: '{original_price}', url: '{url_esc}' " + "}")

    deals_js = "const deals = [\n" + ",\n".join(deals_js_items) + "\n];"

    # Read news JSON (top-3 per category) and build HTML sections + full pages
    import json
    news_public = os.path.join(os.path.dirname(__file__), 'public', 'news')
    news_sections_html = ""
    seen_titles = set()
    for cat, title in [('ai', 'AI 最新'), ('health', '智慧醫療 最新')]:
        json_path = os.path.join(news_public, f"{cat}.json")
        items = []
        try:
            with open(json_path, 'r', encoding='utf-8') as jf:
                items = json.load(jf)
        except Exception:
            items = []
        # dedupe titles across categories to avoid identical 'see more' pages
        filtered_items = []
        for it in items:
            t = (it.get('title') or '').strip()
            if not t:
                continue
            if t in seen_titles:
                continue
            seen_titles.add(t)
            filtered_items.append(it)

        # build top-3 preview
        preview_html = ''
        for item in filtered_items[:3]:
            preview_html += f"""
                <div class=\"market-item\">\n                    <div class=\"asset-info\">\n                        <span class=\"asset-name\">{item.get('title')}</span>\n                        <span class=\"asset-price\">{item.get('source')}</span>\n                    </div>\n                    <div style=\"width:100%;margin-top:0.5rem;\">{item.get('summary')} <a href=\"{item.get('link')}\" target=\"_blank\">（原文）</a></div>\n                </div>"""
        if preview_html:
            news_sections_html += f"""
            <section class=\"card\">\n                <h2>{title} <span>📰</span></h2>\n                <div class=\"market-list\">{preview_html}</div>\n                <div style=\"text-align:right;margin-top:0.5rem;\"><a href=\"news_{cat}.html\">更多{title}</a></div>\n            </section>"""
        # build full page for this category
        full_items_html = ''
        for item in filtered_items:
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
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        # If original HTML missing, use a minimal template
        print(f"Warning: original index.html missing, creating minimal template: {e}")
        html_content = "<!doctype html><html><head><meta charset=\"utf-8\"></head><body><main></main></body></html>"

    # Replace the <main> content
    start_tag = "<main>"
    end_tag = "</main>"
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    if start_idx == -1 or end_idx == -1:
        # fallback: append main
        new_html = html_content + "<main>" + cards_html + news_sections_html + "</main>"
    else:
        new_html = html_content[:start_idx] + cards_html + news_sections_html + html_content[end_idx:]

    # Replace the static deals array in the JS refreshPromotions() function
    marker_start = 'const deals = ['
    if marker_start in new_html:
        s_idx = new_html.find(marker_start)
        e_idx = new_html.find('];', s_idx)
        if e_idx != -1:
            e_idx += 2  # include the closing ];
            new_html = new_html[:s_idx] + deals_js + new_html[e_idx:]

    # Inject trading flag and last-updated into the page (inject script after <body>)
    generated_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trading_flag_script = f"<script>const TRADING_LIVE = {'true' if trading_now else 'false'}; const PAGE_GENERATED_AT = '{generated_at}';</script>"
    if '<body' in new_html:
        new_html = new_html.replace('<body>', '<body>\n' + trading_flag_script)
    else:
        new_html = trading_flag_script + new_html

    # Inject last-updated into the status bar (replace SYSTEM LIVE with timestamp)
    new_html = new_html.replace('SYSTEM LIVE', f'SYSTEM LIVE — 最後更新: {generated_at}')

    # Update deploy marker comment if present
    if 'DEPLOY_MARKER:' in new_html:
        # simple replace for marker line
        import re
        new_html = re.sub(r'DEPLOY_MARKER: .*', f'DEPLOY_MARKER: {generated_at}', new_html)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f"index.html updated successfully (market cards + promotions injected and news sections generated). Generated at {generated_at}.")

if __name__ == "__main__":
    generate_html()
