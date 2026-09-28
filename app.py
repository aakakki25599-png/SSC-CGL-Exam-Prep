import os
import json
import sqlite3
from datetime import datetime

from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from pyq_data import PYQ_QUESTIONS, NOTES_DATA
except Exception:
    PYQ_QUESTIONS = []
    NOTES_DATA = []

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ssc-cgl-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DB_PATH = os.path.join(os.path.dirname(__file__), "ssc_cgl.db")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

SUBJECTS = {
    "quant": {"en": "Quantitative Aptitude", "hi": "मात्रात्मक योग्यता"},
    "reasoning": {"en": "General Intelligence & Reasoning", "hi": "सामान्य बुद्धिमत्ता एवं तर्कशक्ति"},
    "english": {"en": "English Comprehension", "hi": "अंग्रेज़ी भाषा"},
    "gk": {"en": "General Awareness", "hi": "सामान्य जागरूकता"},
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.role = row["role"]

    @staticmethod
    def get_by_id(user_id):
        row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User(row) if row else None

    @staticmethod
    def get_by_username(username):
        row = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return User(row) if row else None


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


def label(subject_key, lang):
    return SUBJECTS.get(subject_key, {}).get(lang, subject_key)


def seed_default_admin():
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("admin", "admin@ssc.local", generate_password_hash("admin123"), "admin"),
        )
    conn.commit()
    conn.close()


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            month TEXT,
            subject TEXT,
            topic TEXT,
            q_en TEXT,
            q_hi TEXT,
            options_json TEXT,
            answer INTEGER,
            exp_en TEXT,
            exp_hi TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            topic TEXT,
            title_en TEXT,
            title_hi TEXT,
            body_en TEXT,
            body_hi TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            topic TEXT,
            total_attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            accuracy REAL DEFAULT 0,
            last_attempt TEXT
        )
        """
    )
    conn.commit()

    if conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
        for q in PYQ_QUESTIONS:
            conn.execute(
                "INSERT INTO questions (year, month, subject, topic, q_en, q_hi, options_json, answer, exp_en, exp_hi) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    q.get("year"),
                    q.get("month"),
                    q.get("subject"),
                    q.get("topic"),
                    q.get("q_en"),
                    q.get("q_hi"),
                    json.dumps(q.get("options", [])),
                    q.get("answer"),
                    q.get("exp_en"),
                    q.get("exp_hi"),
                ),
            )

    if conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0:
        for n in NOTES_DATA:
            conn.execute(
                "INSERT INTO notes (subject, topic, title_en, title_hi, body_en, body_hi) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    n.get("subject"),
                    n.get("topic"),
                    n.get("title_en"),
                    n.get("title_hi"),
                    n.get("body_en"),
                    n.get("body_hi"),
                ),
            )

    conn.commit()
    conn.close()
    seed_default_admin()


def fetch_questions(subject="", limit=10):
    conn = get_db()
    if subject:
        rows = conn.execute(
            "SELECT * FROM questions WHERE subject = ? ORDER BY RANDOM() LIMIT ?",
            (subject, limit),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_notes(subject=""):
    conn = get_db()
    if subject:
        rows = conn.execute("SELECT * FROM notes WHERE subject = ? ORDER BY topic", (subject,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY subject, topic").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_admin(user):
    return bool(user and user.is_authenticated and getattr(user, "role", "") == "admin")


PAGE_TEMPLATE = """
<!doctype html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --card: #ffffff;
      --primary: #1d4ed8;
      --dark: #0f172a;
      --muted: #64748b;
      --good: #16a34a;
      --bad: #dc2626;
      --border: #dfe7f5;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; font-family: Arial, sans-serif; background: var(--bg); color: var(--dark);
    }
    .topbar {
      background: linear-gradient(135deg, #0f172a, #1d4ed8); color: white;
      padding: 16px 5%; display: flex; justify-content: space-between; align-items: center; gap: 12px;
      position: sticky; top: 0; z-index: 10;
    }
    .brand { font-weight: bold; font-size: 1.1rem; }
    .nav a {
      color: white; margin-left: 10px; text-decoration: none; opacity: 0.9;
    }
    .wrap { max-width: 1100px; margin: 24px auto; padding: 0 16px 32px; }
    .hero {
      background: linear-gradient(135deg, #1d4ed8, #2563eb); color: white;
      padding: 24px; border-radius: 18px; margin-bottom: 16px; box-shadow: 0 12px 25px rgba(29,78,216,0.2);
    }
    .hero h1 { margin: 0 0 8px; }
    .card {
      background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 18px; margin-bottom: 16px; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
    }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
    .subject-box { border-left: 5px solid var(--primary); }
    .btn {
      display: inline-block; background: var(--primary); color: white; border: none; border-radius: 10px; padding: 10px 14px; text-decoration: none; cursor: pointer; margin: 6px 6px 0 0;
    }
    .btn.secondary { background: #64748b; }
    .btn.green { background: var(--good); }
    .btn.red { background: var(--bad); }
    .muted { color: var(--muted); }
    .question { margin-bottom: 18px; }
    .option { background: #f8fafc; border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin: 8px 0; }
    .result-box { padding: 12px; border-radius: 10px; background: #ecfdf5; border-left: 5px solid var(--good); }
    .correct { color: var(--good); font-weight: bold; }
    .wrong { color: var(--bad); font-weight: bold; }
    .form-row { margin-bottom: 10px; }
    input, select, textarea {
      width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; font-size: 1rem; margin-top: 6px;
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid var(--border); }
    @media (max-width: 700px) {
      .topbar { flex-direction: column; align-items: flex-start; }
      .nav { margin-top: 8px; }
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="brand">SSC CGL Smart Prep</div>
    <div class="nav">
      <a href="/">Home</a>
      <a href="/notes?lang={{ lang }}">Notes</a>
      <a href="/quiz?lang={{ lang }}">Mock Test</a>
      <a href="/api/export">Export</a>
      {% if current_user.is_authenticated %}
        <a href="/profile">{{ current_user.username }}</a>
        {% if current_user.role == 'admin' %}<a href="/admin">Admin</a>{% endif %}
        <a href="/logout">Logout</a>
      {% else %}
        <a href="/login">Login</a>
        <a href="/register">Register</a>
      {% endif %}
    </div>
  </div>
  <div class="wrap">
    {{ content | safe }}
  </div>
</body>
</html>
"""


def render_page(title, body, lang="en"):
    return render_template_string(PAGE_TEMPLATE, title=title, content=body, lang=lang, current_user=current_user)


@app.route("/")
def home():
    lang = request.args.get("lang", "en")
    if lang == "hi":
        title = "SSC CGL की तैयारी"
        hero_text = "Hindi + English • Subject-wise • Topic-wise • Objective Mock Tests"
        subjects_text = "विषय"
    else:
        title = "SSC CGL Preparation"
        hero_text = "Hindi + English • Subject-wise • Topic-wise • Objective Mock Tests"
        subjects_text = "Subjects"

    cards = []
    for key, info in SUBJECTS.items():
        label_en = info["en"]
        label_hi = info["hi"]
        cards.append(f'''
            <div class="card subject-box">
              <h3>{label_hi if lang == 'hi' else label_en}</h3>
              <p class="muted">{('Topic-wise notes, questions and practice tests' if lang == 'en' else 'Topic-wise notes, questions और mock tests')}</p>
              <a class="btn" href="/notes?subject={key}&lang={lang}">{('Notes' if lang == 'en' else 'नोट्स')}</a>
              <a class="btn secondary" href="/quiz?subject={key}&lang={lang}">{('Mock' if lang == 'en' else 'मॉक')}</a>
            </div>
        ''')

    body = f'''
        <div class="hero">
            <h1>{title}</h1>
            <p>{hero_text}</p>
            <a class="btn green" href="/?lang={'hi' if lang == 'en' else 'en'}">{('हिन्दी' if lang == 'en' else 'English')}</a>
            <a class="btn" href="/quiz?lang={lang}">{('Start Mock' if lang == 'en' else 'मॉक शुरू करें')}</a>
        </div>
        <div class="card">
            <h2>{subjects_text}</h2>
            <div class="grid">{' '.join(cards)}</div>
        </div>
        <div class="card">
            <h3>{('What this app includes' if lang == 'en' else 'इस ऐप में क्या है')}</h3>
            <ul>
                <li>{('Subject-wise study notes' if lang == 'en' else 'विषयवार अध्ययन नोट्स')}</li>
                <li>{('Objective mock tests with answers' if lang == 'en' else 'उत्तर सहित objective mock tests')}</li>
                <li>{('Hindi and English support' if lang == 'en' else 'हिन्दी और अंग्रेज़ी सपोर्ट')}</li>
                <li>{('Progress tracking and export' if lang == 'en' else 'प्रगति ट्रैकिंग और export')}</li>
            </ul>
        </div>
    '''
    return render_page(title, body, lang)


@app.route("/notes")
def notes():
    lang = request.args.get("lang", "en")
    subject = request.args.get("subject", "")
    rows = fetch_notes(subject)
    options = '<option value="">All subjects / सभी विषय</option>'
    for key, info in SUBJECTS.items():
        sel = ' selected' if key == subject else ''
        options += f'<option value="{key}"{sel}>{info["hi" if lang == "hi" else "en"]}</option>'

    cards_html = ""
    if not rows:
        cards_html = f'<div class="card"><p class="muted">{("No notes found" if lang == "en" else "कोई नोट नहीं मिला")}</p></div>'
    else:
        for row in rows:
            title = row["title_hi"] if lang == "hi" else row["title_en"]
            body_text = row["body_hi"] if lang == "hi" else row["body_en"]
            cards_html += f'''
                <div class="card">
                    <h3>{title}</h3>
                    <p class="muted">{label(row['subject'], lang)} • {row['topic']}</p>
                    <p>{body_text}</p>
                </div>
            '''

    body = f'''
        <div class="card">
          <h1>{('Notes' if lang == 'en' else 'नोट्स')}</h1>
          <form method="get">
            <input type="hidden" name="lang" value="{lang}">
            <select name="subject">{options}</select>
            <button class="btn" type="submit">{('Filter' if lang == 'en' else 'फ़िल्टर')}</button>
          </form>
        </div>
        {cards_html}
    '''
    return render_page('Notes', body, lang)


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    lang = request.args.get("lang", "en")
    subject = request.args.get("subject", "")

    if request.method == "POST":
        rows = fetch_questions(subject)
        total = 0
        correct = 0
        result_html = ""
        for row in rows:
            selected = request.form.get(f"q_{row['id']}")
            if selected is not None:
                total += 1
                if int(selected) == int(row["answer"]):
                    correct += 1
            option_list = json.loads(row["options_json"]) if row["options_json"] else []
            right_ans = option_list[int(row["answer"])] if option_list else ""
            if selected is not None:
                result_html += f'''
                    <div class="card">
                      <p><b>{('Q' if lang == 'en' else 'प्रश्न')}: {row['q_hi'] if lang == 'hi' else row['q_en']}</b></p>
                      <p>{('Your answer' if lang == 'en' else 'आपका उत्तर')}: <b>{option_list[int(selected)] if selected.isdigit() and 0 <= int(selected) < len(option_list) else ''}</b></p>
                      <p class="{'correct' if int(selected) == int(row['answer']) else 'wrong'}">{('Correct' if lang == 'en' else 'सही') if int(selected) == int(row['answer']) else ('Wrong' if lang == 'en' else 'गलत')}</p>
                      <p>{('Explanation' if lang == 'en' else 'व्याख्या')}: {row['exp_hi'] if lang == 'hi' else row['exp_en']}</p>
                    </div>
                '''
        percent = round((correct / total) * 100, 2) if total else 0
        body = f'''
            <div class="card result-box">
              <h2>{('Mock Result' if lang == 'en' else 'मॉक परिणाम')}</h2>
              <p>{('Correct' if lang == 'en' else 'सही')}: <b>{correct}</b> / {total}</p>
              <p>{('Accuracy' if lang == 'en' else 'सटीकता')}: <b>{percent}%</b></p>
              <a class="btn" href="/quiz?subject={subject}&lang={lang}">{('Retake' if lang == 'en' else 'दोबारा')}</a>
            </div>
            {result_html}
        '''
        return render_page('Mock Result', body, lang)

    subject_filter = f"WHERE subject='{subject}'" if subject else ""
    rows = fetch_questions(subject, 10)
    if not rows:
        rows = [
            {
                "id": 0,
                "q_en": "Sample question unavailable",
                "q_hi": "सैंपल प्रश्न उपलब्ध नहीं है",
                "options_json": json.dumps(["Option A", "Option B", "Option C", "Option D"]),
                "answer": 0,
                "exp_en": "This is a placeholder until content is added.",
                "exp_hi": "यह डेटा जोड़ने तक का placeholder है।",
            }
        ]

    list_html = ""
    for i, row in enumerate(rows):
        options = json.loads(row["options_json"]) if row["options_json"] else []
        q_text = row["q_hi"] if lang == "hi" else row["q_en"]
        opts_html = "".join(
            f'<div class="option"><label><input type="radio" name="q_{row["id"]}" value="{j}" required> {opt}</label></div>'
            for j, opt in enumerate(options)
        )
        list_html += f'''
            <div class="card question">
                <h3>{i + 1}. {q_text}</h3>
                {opts_html}
            </div>
        '''

    body = f'''
        <div class="card">
            <h1>{('Mock Test' if lang == 'en' else 'मॉक टेस्ट')}</h1>
            <form method="post">
                <div class="form-row">
                    <label for="subject">{('Subject' if lang == 'en' else 'विषय')}</label>
                    <select id="subject" name="subject" onchange="window.location.href='/quiz?subject=' + this.value + '&lang={lang}'">
                        <option value="">{('All subjects' if lang == 'en' else 'सभी विषय')}</option>
                        {''.join(f'<option value="{key}" {'selected' if key == subject else ''}>{SUBJECTS[key]['hi' if lang == 'hi' else 'en']}</option>' for key in SUBJECTS)}
                    </select>
                </div>
                <input type="hidden" name="lang" value="{lang}">
                {list_html}
                <button class="btn green" type="submit">{('Submit' if lang == 'en' else 'जमा करें')}</button>
            </form>
        </div>
    '''
    return render_page('Mock Test', body, lang)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.get_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Login successful", "success")
            return redirect(url_for("home"))
        flash("Invalid username or password", "error")

    body = '''
        <div class="card">
            <h1>Login / लॉगिन</h1>
            <form method="post">
                <div class="form-row">
                    <label>Username</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-row">
                    <label>Password</label>
                    <input type="password" name="password" required>
                </div>
                <button class="btn" type="submit">Login</button>
            </form>
        </div>
    '''
    return render_page('Login', body, request.args.get('lang', 'en'))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not email or not password:
            flash("All fields are required", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for("register"))
        if User.get_by_username(username):
            flash("Username already exists", "error")
            return redirect(url_for("register"))

        conn = get_db()
        conn.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, generate_password_hash(password), "user"),
        )
        conn.commit()
        conn.close()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    body = '''
        <div class="card">
            <h1>Register / रजिस्टर</h1>
            <form method="post">
                <div class="form-row">
                    <label>Username</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-row">
                    <label>Email</label>
                    <input type="email" name="email" required>
                </div>
                <div class="form-row">
                    <label>Password</label>
                    <input type="password" name="password" required>
                </div>
                <div class="form-row">
                    <label>Confirm Password</label>
                    <input type="password" name="confirm" required>
                </div>
                <button class="btn" type="submit">Register</button>
            </form>
        </div>
    '''
    return render_page('Register', body, request.args.get('lang', 'en'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "success")
    return redirect(url_for("home"))


@app.route("/profile")
@login_required
def profile():
    body = f'''
        <div class="card">
          <h1>Profile</h1>
          <p><b>Username:</b> {current_user.username}</p>
          <p><b>Email:</b> {current_user.email}</p>
          <p><b>Role:</b> {current_user.role}</p>
          <a class="btn" href="/">Back to Home</a>
        </div>
    '''
    return render_page('Profile', body, 'en')


@app.route("/admin")
@login_required
def admin_panel():
    if not is_admin(current_user):
        flash("Admin access required", "error")
        return redirect(url_for("login"))

    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    total_notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    conn.close()

    body = f'''
        <div class="card">
            <h1>Admin Dashboard</h1>
            <div class="grid">
                <div class="card"><h3>Users</h3><p>{total_users}</p></div>
                <div class="card"><h3>Questions</h3><p>{total_questions}</p></div>
                <div class="card"><h3>Notes</h3><p>{total_notes}</p></div>
            </div>
        </div>
        <div class="card">
            <h2>Admin Controls</h2>
            <p><a class="btn" href="/admin/add-question">Add Question</a></p>
            <p><a class="btn secondary" href="/admin/add-note">Add Note</a></p>
        </div>
    '''
    return render_page('Admin', body, 'en')


@app.route("/admin/add-question", methods=["GET", "POST"])
@login_required
def add_question():
    if not is_admin(current_user):
        flash("Admin access required", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO questions (year, month, subject, topic, q_en, q_hi, options_json, answer, exp_en, exp_hi) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                request.form.get("year"),
                request.form.get("month"),
                request.form.get("subject"),
                request.form.get("topic"),
                request.form.get("q_en"),
                request.form.get("q_hi"),
                json.dumps(request.form.getlist("option[]")),
                int(request.form.get("answer", 0)),
                request.form.get("exp_en"),
                request.form.get("exp_hi"),
            ),
        )
        conn.commit()
        conn.close()
        flash("Question added successfully", "success")
        return redirect(url_for("admin_panel"))

    body = '''
        <div class="card">
            <h1>Add Question</h1>
            <form method="post">
                <div class="form-row"><label>Year</label><input type="number" name="year" required></div>
                <div class="form-row"><label>Month</label><input type="text" name="month" required></div>
                <div class="form-row"><label>Subject</label>
                    <select name="subject">
                        <option value="quant">Quantitative</option>
                        <option value="reasoning">Reasoning</option>
                        <option value="english">English</option>
                        <option value="gk">General Awareness</option>
                    </select>
                </div>
                <div class="form-row"><label>Topic</label><input type="text" name="topic" required></div>
                <div class="form-row"><label>Question (English)</label><textarea name="q_en" required></textarea></div>
                <div class="form-row"><label>Question (Hindi)</label><textarea name="q_hi" required></textarea></div>
                <div class="form-row"><label>Option 1</label><input type="text" name="option[]" required></div>
                <div class="form-row"><label>Option 2</label><input type="text" name="option[]" required></div>
                <div class="form-row"><label>Option 3</label><input type="text" name="option[]" required></div>
                <div class="form-row"><label>Option 4</label><input type="text" name="option[]" required></div>
                <div class="form-row"><label>Correct Option Index (0-3)</label><input type="number" name="answer" min="0" max="3" required></div>
                <div class="form-row"><label>Explanation (English)</label><textarea name="exp_en" required></textarea></div>
                <div class="form-row"><label>Explanation (Hindi)</label><textarea name="exp_hi" required></textarea></div>
                <button class="btn green" type="submit">Save Question</button>
            </form>
        </div>
    '''
    return render_page('Add Question', body, 'en')


@app.route("/admin/add-note", methods=["GET", "POST"])
@login_required
def add_note():
    if not is_admin(current_user):
        flash("Admin access required", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO notes (subject, topic, title_en, title_hi, body_en, body_hi) VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.form.get("subject"),
                request.form.get("topic"),
                request.form.get("title_en"),
                request.form.get("title_hi"),
                request.form.get("body_en"),
                request.form.get("body_hi"),
            ),
        )
        conn.commit()
        conn.close()
        flash("Note added successfully", "success")
        return redirect(url_for("admin_panel"))

    body = '''
        <div class="card">
            <h1>Add Note</h1>
            <form method="post">
                <div class="form-row"><label>Subject</label>
                    <select name="subject">
                        <option value="quant">Quantitative</option>
                        <option value="reasoning">Reasoning</option>
                        <option value="english">English</option>
                        <option value="gk">General Awareness</option>
                    </select>
                </div>
                <div class="form-row"><label>Topic</label><input type="text" name="topic" required></div>
                <div class="form-row"><label>Title (English)</label><input type="text" name="title_en" required></div>
                <div class="form-row"><label>Title (Hindi)</label><input type="text" name="title_hi" required></div>
                <div class="form-row"><label>Body (English)</label><textarea name="body_en" required></textarea></div>
                <div class="form-row"><label>Body (Hindi)</label><textarea name="body_hi" required></textarea></div>
                <button class="btn green" type="submit">Save Note</button>
            </form>
        </div>
    '''
    return render_page('Add Note', body, 'en')


@app.route("/api/export")
def export_data():
    conn = get_db()
    rows = conn.execute("SELECT * FROM questions ORDER BY year DESC, id DESC").fetchall()
    conn.close()
    data = [dict(r) for r in rows]
    for item in data:
        item["options"] = json.loads(item["options_json"]) if item.get("options_json") else []
        item.pop("options_json", None)
    return jsonify(data)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    init_db()
