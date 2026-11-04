"""SQLite task store for persistent task tracking and audit log."""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

class TaskStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                raw_request TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                investigation_json TEXT,
                implementation_json TEXT,
                review_json TEXT,
                approval_json TEXT,
                iteration_count INTEGER DEFAULT 1,
                final_report TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                channel TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            );
            """)
            conn.commit()

    def save_task(self, state: Dict[str, Any]):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO tasks (
                task_id, raw_request, task_type, status, repo_path,
                investigation_json, implementation_json, review_json, approval_json,
                iteration_count, final_report, error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                status = excluded.status,
                task_type = excluded.task_type,
                investigation_json = excluded.investigation_json,
                implementation_json = excluded.implementation_json,
                review_json = excluded.review_json,
                approval_json = excluded.approval_json,
                iteration_count = excluded.iteration_count,
                final_report = excluded.final_report,
                error = excluded.error,
                updated_at = excluded.updated_at;
            """, (
                state["task_id"],
                state["raw_request"],
                state.get("task_type", "bug"),
                state.get("status", "submitted"),
                state["repo_path"],
                json.dumps(state.get("investigation")) if state.get("investigation") else None,
                json.dumps(state.get("implementation")) if state.get("implementation") else None,
                json.dumps(state.get("review")) if state.get("review") else None,
                json.dumps(state.get("approval")) if state.get("approval") else None,
                state.get("iteration_count", 1),
                state.get("final_report"),
                state.get("error"),
                now,
                now
            ))
            conn.commit()

    def record_message(self, task_id: str, sender: str, recipient: str, channel: str, content: str):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO messages (task_id, sender, recipient, channel, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, sender, recipient, channel, content, now))
            conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            if data["investigation_json"]:
                data["investigation"] = json.loads(data["investigation_json"])
            if data["implementation_json"]:
                data["implementation"] = json.loads(data["implementation_json"])
            if data["review_json"]:
                data["review"] = json.loads(data["review_json"])
            if data["approval_json"]:
                data["approval"] = json.loads(data["approval_json"])
            return data

    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.list_tasks(limit=limit)

    def get_messages(self, task_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE task_id = ? ORDER BY id ASC", (task_id,))
            return [dict(row) for row in cursor.fetchall()]
