from flask import Flask, request, render_template, redirect, session
import sqlite3
import random
import string
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect('database.db')

def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT NOT NULL,
            short TEXT UNIQUE NOT NULL,
            clicks INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

create_tables()

# ---------------- HELPERS ----------------
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def is_logged_in():
    return 'user' in session

# ---------------- ROUTES ----------------
@app.route('/', methods=['GET', 'POST'])
def home():
    if not is_logged_in():
        return redirect('/login')

    message = ''
    short_url = ''
    clicks = None

    if request.method == 'POST':
        original_url = request.form.get('url')
        short_code = request.form.get('custom')

        if not original_url:
            return render_template('index.html', message="Please enter a URL", username=session['user'])

        conn = get_db()
        cursor = conn.cursor()

        if not short_code:
            while True:
                short_code = generate_code()
                cursor.execute('SELECT * FROM urls WHERE short = ?', (short_code,))
                if not cursor.fetchone():
                    break

        cursor.execute('SELECT * FROM urls WHERE short = ?', (short_code,))
        result = cursor.fetchone()

        base_url = request.host_url  # ✅ FIXED

        if result:
            message = "Short code already exists"
            short_url = f"{base_url}{short_code}"
            clicks = result[3]
        else:
            cursor.execute(
                'INSERT INTO urls (original, short, clicks) VALUES (?, ?, 0)',
                (original_url, short_code)
            )
            conn.commit()
            message = "URL shortened successfully!"
            short_url = f"{base_url}{short_code}"
            clicks = 0

        conn.close()

    return render_template(
        'index.html',
        message=message,
        short_url=short_url,
        clicks=clicks,
        username=session['user']
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM users WHERE username=? AND password=?',
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            message = "Invalid credentials"

    return render_template('login.html', message=message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, password)
            )
            conn.commit()
            message = "Signup successful! Please login."
        except sqlite3.IntegrityError:
            message = "User already exists"
        conn.close()

    return render_template('signup.html', message=message)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/<code>')
def redirect_to_url(code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM urls WHERE short = ?', (code,))
    result = cursor.fetchone()

    if result:
        cursor.execute(
            'UPDATE urls SET clicks = clicks + 1 WHERE short = ?',
            (code,)
        )
        conn.commit()
        url = result[1]
        conn.close()
        return redirect(url)
    else:
        conn.close()
        return "URL not found"

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM urls')
    rows = cursor.fetchall()
    conn.close()

    urls = []
    for row in rows:
        urls.append({
            'id': row[0],
            'original_url': row[1],
            'short_code': row[2],
            'visits': row[3]
        })

    labels = [url['short_code'] for url in urls]
    values = [url['visits'] for url in urls]

    return render_template(
        'dashboard.html',
        urls=urls,
        labels=labels,
        values=values,
        username=session['user']
    )

@app.route('/delete/<code>')
def delete(code):
    if not is_logged_in():
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM urls WHERE short = ?', (code,))
    conn.commit()
    conn.close()

    return redirect('/dashboard')

# ✅ IMPORTANT FOR DEPLOYMENT
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)