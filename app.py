from flask import Flask, render_template, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_FILE = "onboard.db"

# ========== ПРОСТОЙ ТЕСТ ==========
@app.route('/')
def home():
    return """
    <h1>🚀 Дашборд работает!</h1>
    <p>Проверка: <a href="/ping">/ping</a></p>
    """

@app.route('/ping')
def ping():
    return "pong"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
