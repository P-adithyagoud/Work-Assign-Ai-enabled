-- ProjectAssign SQL Database Schema (Supabase / PostgreSQL compatible)
-- Paste this script directly into the Supabase SQL Editor and click 'Run'.

-- Drop existing tables (in reverse order of foreign keys)
DROP TABLE IF EXISTS utilization_metrics CASCADE;
DROP TABLE IF EXISTS forecasts CASCADE;
DROP TABLE IF EXISTS activity_logs CASCADE;
DROP TABLE IF EXISTS risks CASCADE;
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS sprints CASCADE;
DROP TABLE IF EXISTS task_dependencies CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS assignment_reports CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Project Manager',
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')
);

-- 2. Employees Table
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    employee_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    skills TEXT NOT NULL,
    experience REAL NOT NULL,
    role TEXT NOT NULL,
    availability TEXT NOT NULL,
    performance_score REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')
);

-- 3. Assignment Reports Table
CREATE TABLE assignment_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_name TEXT NOT NULL,
    project_payload TEXT NOT NULL,
    deterministic_result TEXT NOT NULL,
    ai_result TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 4. Projects Table
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'Planning',
    progress INTEGER NOT NULL DEFAULT 0,
    deadline TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium',
    health_score REAL NOT NULL DEFAULT 100,
    owner_id INTEGER,
    team_member_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    updated_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 5. Tasks Table
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
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
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    updated_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
);

-- 6. Task Dependencies Table
CREATE TABLE task_dependencies (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    depends_on_task_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- 7. Sprints Table
CREATE TABLE sprints (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    capacity_hours REAL NOT NULL DEFAULT 0,
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 8. Notifications Table
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    project_id INTEGER,
    task_id INTEGER,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- 9. Comments Table
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    task_id INTEGER,
    parent_id INTEGER,
    user_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    mentions TEXT NOT NULL DEFAULT '[]',
    attachment_file_id INTEGER,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 10. Files Table
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    task_id INTEGER,
    uploaded_by INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE CASCADE
);

-- 11. Risks Table
CREATE TABLE risks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    risk TEXT NOT NULL,
    probability TEXT NOT NULL,
    impact TEXT NOT NULL,
    mitigation TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 12. Activity Logs Table
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    task_id INTEGER,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 13. Forecasts Table
CREATE TABLE forecasts (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    completion_date TEXT,
    delay_probability REAL NOT NULL DEFAULT 0,
    resource_shortages TEXT NOT NULL DEFAULT '[]',
    velocity_trend TEXT NOT NULL DEFAULT 'Stable',
    recommendations TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 14. Utilization Metrics Table
CREATE TABLE utilization_metrics (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    employee_id TEXT NOT NULL,
    assigned_hours REAL NOT NULL DEFAULT 0,
    capacity_hours REAL NOT NULL DEFAULT 40,
    utilization REAL NOT NULL DEFAULT 0,
    availability TEXT NOT NULL DEFAULT 'Available',
    indicator TEXT NOT NULL DEFAULT 'Green',
    created_at TEXT NOT NULL DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);
