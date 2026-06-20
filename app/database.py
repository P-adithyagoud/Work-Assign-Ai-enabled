import os
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
from flask import g, current_app

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        # Convert SQLite '?' placeholders to PostgreSQL '%s'
        query = query.replace('?', '%s')
        
        # If it's an INSERT statement, automatically append " RETURNING id" if not present
        # so we can populate self.lastrowid
        if query.strip().upper().startswith("INSERT"):
            if "RETURNING" not in query.upper():
                query = query.rstrip().rstrip(';') + " RETURNING id"
            self.cursor.execute(query, params)
            try:
                row = self.cursor.fetchone()
                if row:
                    self.lastrowid = row[0]
            except Exception:
                pass
        else:
            self.cursor.execute(query, params)
        return self

    def fetchone(self):
        try:
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception:
            return None

    def fetchall(self):
        try:
            rows = self.cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None:
                break
            yield row

    def close(self):
        self.cursor.close()

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor(cursor_factory=DictCursor))

    def execute(self, query, params=None):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor

    def executescript(self, script_text):
        cursor = self.conn.cursor()
        cursor.execute(script_text)
        self.conn.commit()
        cursor.close()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

def get_db():
    """Get database connection (PostgreSQL/Supabase if configured, fallback to SQLite)."""
    if 'db' not in g:
        db_url = current_app.config['DATABASE']
        is_postgres = db_url.startswith('postgresql://') or db_url.startswith('postgres://')
        
        if is_postgres:
            # Supabase requires SSL — append sslmode=require if not already present
            if 'sslmode' not in db_url:
                sep = '&' if '?' in db_url else '?'
                db_url = db_url + sep + 'sslmode=require'
            try:
                conn = psycopg2.connect(db_url)
                conn.autocommit = False
                g.db = PostgresConnectionWrapper(conn)
                current_app.logger.info("Connected to Supabase PostgreSQL successfully.")
            except Exception as e:
                current_app.logger.error(f"PostgreSQL connection failed: {e}")
                raise
        else:
            g.db = sqlite3.connect(db_url)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA journal_mode=WAL")
            g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize all database tables (PostgreSQL/Supabase or SQLite)."""
    db = get_db()
    if isinstance(db, PostgresConnectionWrapper):
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Project Manager',
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                skills TEXT NOT NULL,
                experience REAL NOT NULL,
                role TEXT NOT NULL,
                availability TEXT NOT NULL,
                performance_score REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS assignment_reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                project_name TEXT NOT NULL,
                project_payload TEXT NOT NULL,
                deterministic_result TEXT NOT NULL,
                ai_result TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'Planning',
                progress INTEGER NOT NULL DEFAULT 0,
                deadline TEXT,
                priority TEXT NOT NULL DEFAULT 'Medium',
                health_score REAL NOT NULL DEFAULT 100,
                owner_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
                team_member_ids TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')),
                updated_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT,
                assignee_employee_id TEXT,
                priority TEXT NOT NULL DEFAULT 'Medium',
                due_date TEXT,
                estimated_hours REAL NOT NULL DEFAULT 0,
                story_points INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'To Do',
                dependencies TEXT NOT NULL DEFAULT '[]',
                created_by INTEGER REFERENCES users (id) ON DELETE SET NULL,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')),
                updated_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS task_dependencies (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
                depends_on_task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS sprints (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                capacity_hours REAL NOT NULL DEFAULT 0,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users (id) ON DELETE CASCADE,
                project_id INTEGER REFERENCES projects (id) ON DELETE CASCADE,
                task_id INTEGER REFERENCES tasks (id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects (id) ON DELETE CASCADE,
                task_id INTEGER REFERENCES tasks (id) ON DELETE CASCADE,
                parent_id INTEGER REFERENCES comments (id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                body TEXT NOT NULL,
                mentions TEXT NOT NULL DEFAULT '[]',
                attachment_file_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS files (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects (id) ON DELETE CASCADE,
                task_id INTEGER REFERENCES tasks (id) ON DELETE CASCADE,
                uploaded_by INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS risks (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
                risk TEXT NOT NULL,
                probability TEXT NOT NULL,
                impact TEXT NOT NULL,
                mitigation TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS activity_logs (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects (id) ON DELETE CASCADE,
                task_id INTEGER REFERENCES tasks (id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS forecasts (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
                completion_date TEXT,
                delay_probability REAL NOT NULL DEFAULT 0,
                resource_shortages TEXT NOT NULL DEFAULT '[]',
                velocity_trend TEXT NOT NULL DEFAULT 'Stable',
                recommendations TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );

            CREATE TABLE IF NOT EXISTS utilization_metrics (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects (id) ON DELETE CASCADE,
                employee_id TEXT NOT NULL,
                assigned_hours REAL NOT NULL DEFAULT 0,
                capacity_hours REAL NOT NULL DEFAULT 40,
                utilization REAL NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT 'Available',
                indicator TEXT NOT NULL DEFAULT 'Green',
                created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'))
            );
        """)
        print("Supabase/PostgreSQL database initialized successfully.")
    else:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Project Manager',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                skills TEXT NOT NULL,
                experience REAL NOT NULL,
                role TEXT NOT NULL,
                availability TEXT NOT NULL,
                performance_score REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS assignment_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_name TEXT NOT NULL,
                project_payload TEXT NOT NULL,
                deterministic_result TEXT NOT NULL,
                ai_result TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'Planning',
                progress INTEGER NOT NULL DEFAULT 0,
                deadline TEXT,
                priority TEXT NOT NULL DEFAULT 'Medium',
                health_score REAL NOT NULL DEFAULT 100,
                owner_id INTEGER,
                team_member_ids TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (owner_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                assignee_employee_id TEXT,
                priority TEXT NOT NULL DEFAULT 'Medium',
                due_date TEXT,
                estimated_hours REAL NOT NULL DEFAULT 0,
                story_points INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'To Do',
                dependencies TEXT NOT NULL DEFAULT '[]',
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS task_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                depends_on_task_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (depends_on_task_id) REFERENCES tasks (id)
            );

            CREATE TABLE IF NOT EXISTS sprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                capacity_hours REAL NOT NULL DEFAULT 0,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                project_id INTEGER,
                task_id INTEGER,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                task_id INTEGER,
                parent_id INTEGER,
                user_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                mentions TEXT NOT NULL DEFAULT '[]',
                attachment_file_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (parent_id) REFERENCES comments (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                task_id INTEGER,
                uploaded_by INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                risk TEXT NOT NULL,
                probability TEXT NOT NULL,
                impact TEXT NOT NULL,
                mitigation TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            );

            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                task_id INTEGER,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                completion_date TEXT,
                delay_probability REAL NOT NULL DEFAULT 0,
                resource_shortages TEXT NOT NULL DEFAULT '[]',
                velocity_trend TEXT NOT NULL DEFAULT 'Stable',
                recommendations TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            );

            CREATE TABLE IF NOT EXISTS utilization_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                employee_id TEXT NOT NULL,
                assigned_hours REAL NOT NULL DEFAULT 0,
                capacity_hours REAL NOT NULL DEFAULT 40,
                utilization REAL NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT 'Available',
                indicator TEXT NOT NULL DEFAULT 'Green',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            );
        """)
        print("SQLite database initialized successfully.")

def init_app(app):
    """Register teardown context and initialize database."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
