import sqlite3
import os
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from datetime import datetime
import json

DB = '/home/joe/.openclaw/workspace/joeclaw.db'
PUBLIC_DIR = '/home/joe/.openclaw/workspace/public/news'

SOURCES = {
    'ai': [
        # arXiv cs.AI recent
        ('arXiv cs.AI', 'https://export.arxiv.org/rss/cs.AI'),
        ('arXiv cs.LG', 'https://export.arxiv.org/rss/cs.LG'),
        ('TechCrunch AI', 'http://feeds.feedburner.com/TechCrunch/'),
        ('The Verge', 'https://www.theverge.com/rss/index.xml')
    ],
    'health': [
        ('Nature Medicine', 'https://www.nature.com/collections/rsfzfmbdvg/rss'),
        ('medRxiv', 'https://connect.medrxiv.org/relate/feed/'),
        ('Stat News Health', 'https://www.statnews.com/feed/'),
        ('MIT Tech Review Health', 'https://www.technologyreview.com/feed/')
    ]
}

# Ensure public dir
os.makedirs(PUBLIC_DIR, exist_ok=True)

# Basic helpers

def fetch_rss(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'JoeClawSite-Agent/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"Warning: failed to fetch {url}: {e}")
        return None


def parse_rss_feed(xml_bytes, limit=5):
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        # try to recover by decoding and replacing bad chars
        try:
            txt = xml_bytes.decode('utf-8', errors='ignore')
            root = ET.fromstring(txt)
        except Exception as e2:
            print(f"Warning: failed to parse feed: {e2}")
            return []

    items = []
    # RSS channel/item or Atom
    for item in root.findall('.//item')[:limit]:
        title = item.findtext('title') or ''
        link = item.findtext('link') or ''
        desc = item.findtext('description') or item.findtext('summary') or ''
        pub = item.findtext('pubDate') or item.findtext('updated') or ''
        items.append({'title': unescape(title).strip(), 'link': link.strip(), 'description': unescape(desc).strip(), 'pubDate': pub.strip()})
    # Atom fallback
    if not items:
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry')[:limit]:
            title = entry.findtext('{http://www.w3.org/2005/Atom}title') or ''
            link_el = entry.find('{http://www.w3.org/2005/Atom}link')
            link = link_el.get('href') if link_el is not None else ''
            summary = entry.findtext('{http://www.w3.org/2005/Atom}summary') or entry.findtext('{http://www.w3.org/2005/Atom}content') or ''
            pub = entry.findtext('{http://www.w3.org/2005/Atom}updated') or entry.findtext('{http://www.w3.org/2005/Atom}published') or ''
            items.append({'title': unescape(title).strip(), 'link': link.strip(), 'description': unescape(summary).strip(), 'pubDate': pub.strip()})
    return items


def short_summary(text, max_sentences=2):
    # crude: split by period, question, exclamation
    import re
    sentences = re.split(r'(?<=[\.\?\!])\s+', text)
    out = ' '.join(sentences[:max_sentences]).strip()
    if not out:
        out = (text[:200] + '...') if text else ''
    return out


def generate_recommendation(category, title):
    # rule-based suggestions; for health include disclaimer
    base = []
    if category == 'ai':
        base.append('追蹤此議題的後續研究與實作示範。')
        base.append('評估是否能在現有專案中擷取可用成果（POC）。')
        base.append('若技術成熟，安排內部討論並列入 roadmap 優先級評估。')
    else:
        base.append('請專業醫療人員審核研究摘要與方法。')
        base.append('評估臨床或產品導入的法規/合規障礙。')
        base.append('若有可測試的技術，安排小範圍試點並記錄效果與安全性。')
    return '；'.join(base[:2])


def store_news(records):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            title TEXT,
            source TEXT,
            url TEXT,
            fetched_at TEXT,
            summary TEXT,
            tags TEXT,
            recommendation TEXT,
            excerpt TEXT
        )
    ''')
    for r in records:
        c.execute('INSERT INTO news (category, title, source, url, fetched_at, summary, tags, recommendation, excerpt) VALUES (?,?,?,?,?,?,?,?,?)', (
            r.get('category'), r.get('title'), r.get('source'), r.get('link'), r.get('fetched_at'), r.get('summary'), ','.join(r.get('tags', [])), r.get('recommendation'), r.get('excerpt')
        ))
    conn.commit()
    conn.close()


def write_public_json(category, items):
    path = os.path.join(PUBLIC_DIR, f'{category}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f'Wrote public JSON: {path}')


def dedupe_keep_latest(entries):
    seen = {}
    out = []
    for e in entries:
        key = (e['title'] or '').lower()
        if not key:
            key = e['link']
        if key in seen:
            # keep latest by fetched_at
            prev = seen[key]
            if e['fetched_at'] > prev['fetched_at']:
                seen[key] = e
        else:
            seen[key] = e
    # return sorted by fetched_at desc
    out = sorted(seen.values(), key=lambda x: x['fetched_at'], reverse=True)
    return out


def run_once():
    all_records = []
    for category, sources in SOURCES.items():
        items_acc = []
        for source_name, url in sources:
            raw = fetch_rss(url)
            if not raw:
                continue
            parsed = parse_rss_feed(raw, limit=6)
            for p in parsed:
                fetched_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                summary = short_summary(p.get('description',''), 2)
                rec = generate_recommendation(category, p.get('title',''))
                excerpt = (p.get('description','')[:300] + '...') if p.get('description') else ''
                item = {
                    'category': category,
                    'title': p.get('title',''),
                    'source': source_name,
                    'link': p.get('link',''),
                    'fetched_at': fetched_at,
                    'summary': summary,
                    'tags': [],
                    'recommendation': rec,
                    'excerpt': excerpt
                }
                items_acc.append(item)
        # dedupe and keep latest 20
        items_acc = dedupe_keep_latest(items_acc)[:20]
        all_records.extend(items_acc)
        # write public JSON for category
        write_public_json(category, items_acc)

    # store into DB
    store_news(all_records)
    print(f'Fetched total news items: {len(all_records)}')

if __name__ == '__main__':
    run_once()
