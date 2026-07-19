"""
Task Manager API
A REST API for a Kanban-style task management app.

Built with Flask, raw SQL (sqlite3), and JWT authentication.
"""

import sqlite3
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Flask, request, jsonify, render_template, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
DATABASE = "tasks.db"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
        );
        """
    )
    db.commit()
    db.close()


def task_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "due_date": row["due_date"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            db = get_db()
            user = db.execute("SELECT * FROM user WHERE id = ?", (payload["user_id"],)).fetchone()
            if user is None:
                raise ValueError("User not found")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        return f(user, *args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Frontend route
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username already taken"}), 409

    password_hash = generate_password_hash(password)
    now = datetime.utcnow().isoformat()
    cursor = db.execute(
        "INSERT INTO user (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, now),
    )
    db.commit()

    token = generate_token(cursor.lastrowid)
    return jsonify({"token": token, "username": username}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    db = get_db()
    user = db.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    token = generate_token(user["id"])
    return jsonify({"token": token, "username": user["username"]}), 200


# ---------------------------------------------------------------------------
# Task routes (CRUD)
# ---------------------------------------------------------------------------

@app.route("/api/tasks", methods=["GET"])
@token_required
def get_tasks(current_user):
    db = get_db()
    status_filter = request.args.get("status")

    if status_filter:
        rows = db.execute(
            "SELECT * FROM task WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
            (current_user["id"], status_filter),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM task WHERE user_id = ? ORDER BY created_at DESC",
            (current_user["id"],),
        ).fetchall()

    return jsonify([task_to_dict(r) for r in rows]), 200


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
@token_required
def get_task(current_user, task_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM task WHERE id = ? AND user_id = ?", (task_id, current_user["id"])
    ).fetchone()
    if row is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task_to_dict(row)), 200


@app.route("/api/tasks", methods=["POST"])
@token_required
def create_task(current_user):
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    status = data.get("status", "todo")
    if status not in ("todo", "in_progress", "done"):
        return jsonify({"error": "status must be todo, in_progress, or done"}), 400

    priority = data.get("priority", "medium")
    if priority not in ("low", "medium", "high"):
        return jsonify({"error": "priority must be low, medium, or high"}), 400

    due_date = data.get("due_date")
    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "due_date must be in YYYY-MM-DD format"}), 400

    now = datetime.utcnow().isoformat()
    db = get_db()
    cursor = db.execute(
        """INSERT INTO task (title, description, status, priority, due_date, created_at, updated_at, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, data.get("description", ""), status, priority, due_date, now, now, current_user["id"]),
    )
    db.commit()

    row = db.execute("SELECT * FROM task WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(task_to_dict(row)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@token_required
def update_task(current_user, task_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM task WHERE id = ? AND user_id = ?", (task_id, current_user["id"])
    ).fetchone()
    if row is None:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True) or {}
    updates = {}

    if "title" in data:
        if not data["title"].strip():
            return jsonify({"error": "Title cannot be empty"}), 400
        updates["title"] = data["title"].strip()
    if "description" in data:
        updates["description"] = data["description"]
    if "status" in data:
        if data["status"] not in ("todo", "in_progress", "done"):
            return jsonify({"error": "status must be todo, in_progress, or done"}), 400
        updates["status"] = data["status"]
    if "priority" in data:
        if data["priority"] not in ("low", "medium", "high"):
            return jsonify({"error": "priority must be low, medium, or high"}), 400
        updates["priority"] = data["priority"]
    if "due_date" in data:
        if data["due_date"]:
            try:
                datetime.strptime(data["due_date"], "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "due_date must be in YYYY-MM-DD format"}), 400
        updates["due_date"] = data["due_date"]

    if not updates:
        return jsonify(task_to_dict(row)), 200

    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    db.execute(f"UPDATE task SET {set_clause} WHERE id = ?", values)
    db.commit()

    updated_row = db.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
    return jsonify(task_to_dict(updated_row)), 200


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@token_required
def delete_task(current_user, task_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM task WHERE id = ? AND user_id = ?", (task_id, current_user["id"])
    ).fetchone()
    if row is None:
        return jsonify({"error": "Task not found"}), 404

    db.execute("DELETE FROM task WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"message": "Task deleted"}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
