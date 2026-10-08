from flask import Flask, request, jsonify, session, send_from_directory
import hashlib, os
import sqlite3
from datetime import date

app = Flask(__name__, static_folder='public')
app.secret_key = os.environ.get('SECRET_KEY', 'dailydriver-secret-2024')

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dailydriver.db'))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            userId INTEGER PRIMARY KEY AUTOINCREMENT,
            userName VARCHAR(50) NOT NULL,
            userEmail VARCHAR(100) NOT NULL UNIQUE,
            userPassword VARCHAR(255) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS habits (
            habitId INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER NOT NULL,
            habitName VARCHAR(100) NOT NULL,
            habitTarget INTEGER DEFAULT 1,
            habitStartDate DATE,
            FOREIGN KEY (userId) REFERENCES users(userId)
        );
        CREATE TABLE IF NOT EXISTS habit_log (
            logId INTEGER PRIMARY KEY AUTOINCREMENT,
            habitId INTEGER NOT NULL,
            logDate DATE NOT NULL,
            status VARCHAR(10) NOT NULL DEFAULT 'not done',
            FOREIGN KEY (habitId) REFERENCES habits(habitId)
        );
    ''')
    conn.commit()
    conn.close()

# ── Serve frontend ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('public', path)

# ── Auth ─────────────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    if not name or not email or not password:
        return jsonify({'error': 'Semua field wajib diisi'}), 400
    salt = os.urandom(16).hex()
    hashed = salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()
    try:
        conn = get_db()
        conn.execute('INSERT INTO users (userName, userEmail, userPassword) VALUES (?, ?, ?)',
                     (name, email, hashed))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Registrasi berhasil'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email sudah terdaftar'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE userEmail = ?', (email,)).fetchone()
    conn.close()
    def verify(stored, pwd):
        salt, h = stored.split(':')
        return hashlib.sha256((salt + pwd).encode()).hexdigest() == h
    if user and verify(user['userPassword'], password):
        session['userId'] = user['userId']
        session['userName'] = user['userName']
        return jsonify({'message': 'Login berhasil', 'name': user['userName']})
    return jsonify({'error': 'Email atau password salah'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout berhasil'})

@app.route('/api/me')
def me():
    if 'userId' not in session:
        return jsonify({'error': 'Belum login'}), 401
    return jsonify({'userId': session['userId'], 'name': session['userName']})

# ── Habits ────────────────────────────────────────────────────────────────────
@app.route('/api/habits', methods=['GET'])
def get_habits():
    if 'userId' not in session:
        return jsonify({'error': 'Belum login'}), 401
    today = date.today().isoformat()
    conn = get_db()
    habits = conn.execute('SELECT * FROM habits WHERE userId = ?', (session['userId'],)).fetchall()
    result = []
    for h in habits:
        log = conn.execute(
            'SELECT * FROM habit_log WHERE habitId = ? AND logDate = ?',
            (h['habitId'], today)
        ).fetchone()
        result.append({
            'habitId': h['habitId'],
            'habitName': h['habitName'],
            'habitTarget': h['habitTarget'],
            'habitStartDate': h['habitStartDate'],
            'status': log['status'] if log else 'not done',
            'logId': log['logId'] if log else None
        })
    conn.close()
    return jsonify(result)

@app.route('/api/habits', methods=['POST'])
def add_habit():
    if 'userId' not in session:
        return jsonify({'error': 'Belum login'}), 401
    data = request.json
    name = data.get('habitName', '').strip()
    target = data.get('habitTarget', 1)
    if not name:
        return jsonify({'error': 'Nama habit wajib diisi'}), 400
    today = date.today().isoformat()
    conn = get_db()
    conn.execute(
        'INSERT INTO habits (userId, habitName, habitTarget, habitStartDate) VALUES (?, ?, ?, ?)',
        (session['userId'], name, target, today)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Habit berhasil ditambahkan'})

@app.route('/api/habits/<int:habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    if 'userId' not in session:
        return jsonify({'error': 'Belum login'}), 401
    conn = get_db()
    conn.execute('DELETE FROM habit_log WHERE habitId = ?', (habit_id,))
    conn.execute('DELETE FROM habits WHERE habitId = ? AND userId = ?', (habit_id, session['userId']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Habit dihapus'})

@app.route('/api/habits/<int:habit_id>/toggle', methods=['POST'])
def toggle_habit(habit_id):
    if 'userId' not in session:
        return jsonify({'error': 'Belum login'}), 401
    today = date.today().isoformat()
    conn = get_db()
    existing = conn.execute(
        'SELECT * FROM habit_log WHERE habitId = ? AND logDate = ?', (habit_id, today)
    ).fetchone()
    if existing:
        new_status = 'done' if existing['status'] == 'not done' else 'not done'
        conn.execute('UPDATE habit_log SET status = ? WHERE logId = ?', (new_status, existing['logId']))
    else:
        conn.execute('INSERT INTO habit_log (habitId, logDate, status) VALUES (?, ?, ?)',
                     (habit_id, today, 'done'))
        new_status = 'done'
    conn.commit()
    conn.close()
    return jsonify({'status': new_status})

# ── History ───────────────────────────────────────────────────────────────────
@app.route('/api/history')
def get_history():
    if 'userId' not in session:
        return jsonify({'error': 'Belum login'}), 401
    conn = get_db()
    logs = conn.execute('''
        SELECT hl.logDate, h.habitName, hl.status
        FROM habit_log hl
        JOIN habits h ON hl.habitId = h.habitId
        WHERE h.userId = ?
        ORDER BY hl.logDate DESC, h.habitName ASC
    ''', (session['userId'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in logs])

# Buat tabel saat modul di-load (diperlukan agar jalan di bawah gunicorn)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"DailyDriver berjalan di http://localhost:{port}")
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=port)
