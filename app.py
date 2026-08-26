from flask import Flask, render_template, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_FILE = "onboard.db"

def init_db():
    """Создаёт таблицы, если их нет"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            day INTEGER DEFAULT 0,
            rating INTEGER,
            completed BOOLEAN DEFAULT 0,
            start_date TEXT,
            completed_date TEXT,
            last_activity TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            day INTEGER,
            total_correct INTEGER,
            total_questions INTEGER,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY start_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_stats():
    users = get_all_users()
    total = len(users)
    completed = sum(1 for u in users if u[4])
    in_progress = total - completed
    ratings = [u[3] for u in users if u[3] is not None]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    day_stats = {}
    for i in range(1, 8):
        count = sum(1 for u in users if u[2] >= i)
        day_stats[i] = count
    
    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'avg_rating': avg_rating,
        'day_stats': day_stats,
        'users': users
    }

@app.route('/')
def dashboard():
    stats = get_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/api/stats')
def api_stats():
    stats = get_stats()
    return jsonify({
        'total': stats['total'],
        'completed': stats['completed'],
        'in_progress': stats['in_progress'],
        'avg_rating': stats['avg_rating'],
        'day_stats': stats['day_stats']
    })

@app.route('/api/users')
def api_users():
    users = get_all_users()
    return jsonify([{
        'id': u[0],
        'name': u[1] or 'Без имени',
        'day': u[2],
        'rating': u[3],
        'completed': bool(u[4]),
        'start_date': u[5],
        'completed_date': u[6]
    } for u in users])

if __name__ == '__main__':
    # Инициализируем БД при старте
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
