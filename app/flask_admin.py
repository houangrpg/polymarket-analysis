from flask import Flask, request, g, render_template_string, redirect
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'data.db')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'change-me')

TEMPLATE = '''
<!doctype html>
<title>Admin - DB</title>
<h2>PK History (latest)</h2>
<table border=1 cellpadding=6>
<tr><th>date</th><th>accuracy</th><th>correct</th><th>total</th></tr>
{% for r in rows %}
<tr><td>{{r[0]}}</td><td>{{r[1]}}</td><td>{{r[2]}}</td><td>{{r[3]}}</td></tr>
{% endfor %}
</table>
<form method="post" action="/admin/add">
<h3>Add / Update PK</h3>
Date: <input name="date" placeholder="YYYY-MM-DD"> Accuracy: <input name="accuracy"> Correct: <input name="correct"> Total: <input name="total"> <button type="submit">Add</button>
</form>
'''


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = None
    return conn

@app.route('/admin')
def admin_index():
    if not os.path.exists(DB_PATH):
        return "DB not found. Run migration first.", 500
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT date, accuracy, correct, total FROM pk_history ORDER BY date DESC LIMIT 60')
    rows = cur.fetchall()
    conn.close()
    return render_template_string(TEMPLATE, rows=rows)

@app.route('/admin/add', methods=['POST'])
def admin_add():
    date = request.form.get('date')
    accuracy = request.form.get('accuracy')
    correct = request.form.get('correct')
    total = request.form.get('total')
    conn = get_db()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS pk_history(date TEXT PRIMARY KEY, accuracy REAL, correct INTEGER, total INTEGER)')
    cur.execute('INSERT OR REPLACE INTO pk_history(date, accuracy, correct, total) VALUES (?,?,?,?)', (date, accuracy or 0, correct or 0, total or 0))
    conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
