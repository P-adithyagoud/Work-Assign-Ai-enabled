import os
import sqlite3
import json
from datetime import datetime
from flask import g, current_app


def get_db():
    """Get SQLite database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
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
    """Initialize all database tables."""
    db = get_db()
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
    db.commit()
    print("SQLite database initialized successfully.")


def init_app(app):
    """Register teardown context and initialize database."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
