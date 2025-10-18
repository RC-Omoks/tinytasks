# TinyTasks (Mini Full‑Stack App)

A super small, single‑file full‑stack app you can run locally that still feels like “real” web dev:
- **Frontend:** Flask + Jinja templates (HTML/CSS inlined for simplicity)
- **Backend:** Flask routes (server‑side rendering)
- **Database:** SQLite (file `tinytasks.db`), raw SQL
- **Auth (demo):** simple username sign‑in stored in session (no passwords)
- **Features:** Create tasks, toggle done, delete, and see a progress bar

## Quickstart
```bash
python3 -m venv .venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install flask
python tinytasks.py
# open http://127.0.0.1:5000
```

- **UI layer:** HTML templates, forms, and CSS, rendered by server
- **Server layer:** Flask routes handle requests, validate input, enforce per‑user scoping
- **Data layer:** SQLite persists users and tasks, with simple schema + CRUD

## Schema
- `users(id, username UNIQUE)`
- `tasks(id, user_id -> users.id, title, done)`

## Notes
- This is a teaching/demo app. For production, add real auth, CSRF protection, better error handling, and tests.
