from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB_FILE = "onboard.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY start_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_stats():
    users = get_all_users()
    total = len(users)
    completed = sum(1 for u in users if u['completed'])
    in_progress = total - completed
    ratings = [u['rating'] for u in users if u['rating'] is not None]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    # Статистика по дням
    day_stats = {}
    for i in range(1, 8):
        count = sum(1 for u in users if u['day'] >= i)
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
        'id': u['user_id'],
        'name': u['name'] or 'Без имени',
        'day': u['day'],
        'rating': u['rating'],
        'completed': bool(u['completed']),
        'start_date': u['start_date'],
        'completed_date': u['completed_date']
    } for u in users])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)