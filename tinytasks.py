#!/usr/bin/env python3
from __future__ import annotations
import os
import sqlite3
from dataclasses import dataclass
from typing import List, Optional
from flask import Flask, g, redirect, render_template, request, session, url_for, flash
from jinja2 import DictLoader

# -----------------------------
# Config
# -----------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")  # replace in prod
DB_PATH = os.environ.get("DB_PATH", "tinytasks.db")

# -----------------------------
# Templates 
# -----------------------------
BASE_TEMPLATE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TinyTasks</title>
  <style>
    :root { --bg:#0b0b0f; --card:#12121a; --muted:#9aa0aa; --text:#f5f7fa; --accent:#4f46e5; --ok:#16a34a; --warn:#ef4444;}
    html,body { margin:0; padding:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji'; background:var(--bg); color:var(--text); }
    .wrap { max-width: 800px; margin: 40px auto; padding: 0 16px; }
    .card { background: var(--card); border: 1px solid #1f2937; border-radius:16px; padding: 20px; }
    .row { display:flex; gap:12px; align-items:center; }
    .space { height: 16px; }
    .btn { background: var(--accent); border:none; color:white; padding:10px 14px; border-radius:10px; cursor:pointer; font-weight:600; }
    .btn.secondary { background: transparent; border:1px solid #2b3240; color: var(--text); }
    .btn.danger { background: var(--warn); }
    input[type=text] { width:100%; padding:10px 12px; border-radius:10px; border:1px solid #2b3240; background:#0f1116; color:var(--text); }
    .task { display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:1px solid #1f2937; }
    .task:last-child { border-bottom:none; }
    .task .title.done { text-decoration: line-through; color: var(--muted); }
    .muted { color: var(--muted); }
    .progress { height:10px; width:100%; background:#0f1116; border-radius:999px; overflow:hidden; border:1px solid #2b3240; }
    .bar { height:100%; background: linear-gradient(90deg, var(--ok), #22c55e); }
    .header { display:flex; justify-content:space-between; align-items:center; }
    a { color:#93c5fd; text-decoration:none; }
    .flash { background:#111827; border:1px solid #374151; padding:10px 12px; border-radius:10px; margin-bottom:12px;}
  </style>
</head>
<body>
  <div class="wrap">
    {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="flash">{{ messages[0] }}</div>
    {% endif %}
    {% endwith %}

    <div class="card">
      <div class="header">
        <h1>TinyTasks</h1>
        {% if session.uid %}
          <div class="row">
            <span class="muted">Signed in as <strong>{{ session.username }}</strong></span>
            <a href="{{ url_for('logout') }}" class="btn secondary">Logout</a>
          </div>
        {% endif %}
      </div>
      <div class="space"></div>
      {% block content %}{% endblock %}
    </div>
  </div>
</body>
</html>
"""

LOGIN_TEMPLATE = r"""
{% extends "base.html" %}
{% block content %}
  <h2>Welcome</h2>
  <p class="muted">Sign in with a simple username (demo). This keeps your tasks separate.</p>
  <form method="post" class="row" style="margin-top:12px">
    <input type="text" name="username" placeholder="e.g. daniel" required>
    <button class="btn" type="submit">Sign in</button>
  </form>
{% endblock %}
"""

INDEX_TEMPLATE = r"""
{% extends "base.html" %}
{% block content %}
  <div class="row">
    <form method="post" action="{{ url_for('add_task') }}" class="row" style="flex:1">
      <input type="text" name="title" placeholder="Add a new task..." required>
      <button class="btn" type="submit">Add</button>
    </form>
  </div>

  <div class="space"></div>

  {% set total = tasks|length %}
  {% set done = tasks|selectattr('done')|list|length %}
  {% set pct = (done * 100 // (total if total>0 else 1)) %}

  <div>
    <div class="row" style="justify-content:space-between;">
      <span class="muted">Progress</span>
      <span>{{ done }}/{{ total }} ({{ pct }}%)</span>
    </div>
    <div class="progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{{ pct }}">
      <div class="bar" style="width: {{ pct }}%"></div>
    </div>
  </div>

  <div class="space"></div>

  {% if tasks %}
    {% for t in tasks %}
      <div class="task">
        <div class="row">
          <form method="post" action="{{ url_for('toggle_task', task_id=t.id) }}">
            <button class="btn secondary" type="submit">{{ "✅" if t.done else "⬜️" }}</button>
          </form>
          <span class="title {{ 'done' if t.done else '' }}">{{ t.title }}</span>
        </div>
        <form method="post" action="{{ url_for('delete_task', task_id=t.id) }}">
          <button class="btn danger" type="submit">Delete</button>
        </form>
      </div>
    {% endfor %}
  {% else %}
    <p class="muted">No tasks yet. Add your first one above.</p>
  {% endif %}
{% endblock %}
"""

app.jinja_loader = DictLoader({
    "base.html": BASE_TEMPLATE,
    "login.html": LOGIN_TEMPLATE,
    "index.html": INDEX_TEMPLATE,
})

# -----------------------------
# DB helpers
# -----------------------------
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    db.commit()

# -----------------------------
# Models 
# -----------------------------
@dataclass
class Task:
    id: int
    user_id: int
    title: str
    done: int

    @staticmethod
    def all_for_user(db: sqlite3.Connection, user_id: int) -> List["Task"]:
        rows = db.execute(
            "SELECT id, user_id, title, done FROM tasks WHERE user_id = ? ORDER BY created_at ASC",
            (user_id,),
        ).fetchall()
        return [Task(**dict(r)) for r in rows]

    @staticmethod
    def create(db: sqlite3.Connection, user_id: int, title: str) -> None:
        db.execute("INSERT INTO tasks(user_id, title, done) VALUES(?, ?, 0)", (user_id, title))
        db.commit()

    @staticmethod
    def toggle(db: sqlite3.Connection, task_id: int, user_id: int) -> None:
        row = db.execute(
            "SELECT done FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()
        if not row:
            return
        new_val = 0 if row["done"] else 1
        db.execute("UPDATE tasks SET done = ? WHERE id = ? AND user_id = ?", (new_val, task_id, user_id))
        db.commit()

    @staticmethod
    def delete(db: sqlite3.Connection, task_id: int, user_id: int) -> None:
        db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        db.commit()

# -----------------------------
# Auth helpers 
# -----------------------------
def current_user_id() -> Optional[int]:
    return session.get("uid")

def get_or_create_user(db: sqlite3.Connection, username: str) -> int:
    row = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return int(row["id"])
    cur = db.execute("INSERT INTO users(username) VALUES(?)", (username,))
    db.commit()
    return int(cur.lastrowid)

@app.before_request
def _ensure_db():
    init_db()

# -----------------------------
# Routes
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        if not username:
            flash("Username is required.")
            return redirect(url_for("login"))
        db = get_db()
        uid = get_or_create_user(db, username)
        session["uid"] = uid
        session["username"] = username
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/", methods=["GET"])
def index():
    if not current_user_id():
        return redirect(url_for("login"))
    db = get_db()
    tasks = Task.all_for_user(db, current_user_id())
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
def add_task():
    if not current_user_id():
        return redirect(url_for("login"))
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title cannot be empty.")
        return redirect(url_for("index"))
    db = get_db()
    Task.create(db, current_user_id(), title)
    return redirect(url_for("index"))

@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle_task(task_id: int):
    if not current_user_id():
        return redirect(url_for("login"))
    db = get_db()
    Task.toggle(db, task_id, current_user_id())
    return redirect(url_for("index"))

@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id: int):
    if not current_user_id():
        return redirect(url_for("login"))
    db = get_db()
    Task.delete(db, task_id, current_user_id())
    return redirect(url_for("index"))

if __name__ == "__main__":
    print("TinyTasks running at http://127.0.0.1:5000")
    app.run(debug=True)
