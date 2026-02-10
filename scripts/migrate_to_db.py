#!/usr/bin/env python3
import sqlite3, json, os
from pathlib import Path

DATA_DIR = Path('data')
DB_PATH = DATA_DIR / 'data.db'
DATA_DIR.mkdir(exist_ok=True)

def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS pk_history (
        date TEXT PRIMARY KEY,
        accuracy REAL,
        correct INTEGER,
        total INTEGER
    )''')
    conn.commit()

def migrate_prediction_history(conn):
    jfile = Path('prediction_history.json')
    if not jfile.exists():
        print('No prediction_history.json found, skipping')
        return
    try:
        with open(jfile, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print('Failed to read prediction_history.json:', e)
        return
    cur = conn.cursor()
    for entry in data:
        try:
            cur.execute('INSERT OR REPLACE INTO pk_history(date, accuracy, correct, total) VALUES (?,?,?,?)',
                        (entry.get('date'), float(entry.get('accuracy') or 0), int(entry.get('correct') or 0), int(entry.get('total') or 0)))
        except Exception as e:
            print('skip entry', entry, 'error', e)
    conn.commit()
    print('Migrated', len(data), 'rows into pk_history')

if __name__ == '__main__':
    conn = sqlite3.connect(str(DB_PATH))
    ensure_schema(conn)
    migrate_prediction_history(conn)
    conn.close()
    print('Done. DB at', DB_PATH)
