# TaskBoard — Full-Stack Task Manager

A Kanban-style task management web app with a REST API backend. Built to
demonstrate full-stack development: authentication, a database-backed API,
and a responsive frontend that consumes it.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-black)

## Features

- 🔐 **JWT authentication** — register/login, tokens expire after 24 hours
- 📋 **Full CRUD** on tasks via a REST API (create, read, update, delete)
- 🖱️ **Drag-and-drop** Kanban board (To Do / In Progress / Done)
- 🎯 **Priority levels & due dates** per task
- 🗄️ **SQLite database** with raw SQL (no ORM) — every query is explicit
- 📱 **Responsive UI** — works on desktop and mobile

## Tech Stack

| Layer      | Technology                         |
|------------|-------------------------------------|
| Backend    | Python, Flask, SQLite (`sqlite3`)  |
| Auth       | PyJWT, Werkzeug password hashing   |
| Frontend   | HTML5, CSS3, vanilla JavaScript    |

No frontend framework or ORM is used on purpose — it keeps the codebase small
and makes every part of the request lifecycle (HTTP → auth → SQL → JSON →
DOM) visible and easy to explain in an interview.

## Project Structure

```
task-manager/
├── app.py                 # Flask app: routes, auth, database logic
├── requirements.txt
├── templates/
│   └── index.html         # Single-page app shell
└── static/
    ├── style.css
    └── app.js              # Auth flow, API calls, drag-and-drop
```

## Setup

1. **Clone and enter the project**
   ```bash
   git clone <your-repo-url>
   cd task-manager
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   python app.py
   ```
   The database (`tasks.db`) is created automatically on first run.

5. Open **http://127.0.0.1:5000** in your browser.

## API Reference

All `/api/tasks*` routes require an `Authorization: Bearer <token>` header,
obtained from `/api/register` or `/api/login`.

| Method | Endpoint             | Description                     |
|--------|-----------------------|----------------------------------|
| POST   | `/api/register`       | Create a new user account       |
| POST   | `/api/login`          | Log in, returns a JWT           |
| GET    | `/api/tasks`          | List all tasks for current user |
| GET    | `/api/tasks/<id>`     | Get a single task               |
| POST   | `/api/tasks`          | Create a task                   |
| PUT    | `/api/tasks/<id>`     | Update a task (partial updates) |
| DELETE | `/api/tasks/<id>`     | Delete a task                   |

Example: creating a task with `curl`

```bash
curl -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"title": "Finish CV", "priority": "high", "due_date": "2026-07-20"}'
```

## Author

Cameron Manipersad — [GitHub](https://github.com/CameronManipersad) ·
[LinkedIn](https://www.linkedin.com/in/cameronmanipersad)
