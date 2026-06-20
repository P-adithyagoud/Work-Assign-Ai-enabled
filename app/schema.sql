-- ProjectAssign SQL Database Schema (PostgreSQL/Supabase compatible)

-- Drop tables if they exist in reverse order of foreign keys
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS milestones CASCADE;
DROP TABLE IF EXISTS assignments CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- 2. Employees Table
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(150) NOT NULL,
    skills TEXT NOT NULL, -- Comma-separated tags
    experience INTEGER NOT NULL, -- Years of experience
    availability VARCHAR(50) NOT NULL, -- Availability status
    performance_score INTEGER NOT NULL -- Performance score out of 100
);

-- 3. Projects Table
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    duration VARCHAR(100) NOT NULL, -- Duration string
    team_size INTEGER NOT NULL,
    technologies TEXT NOT NULL, -- Comma-separated tags
    preferred_roles TEXT NOT NULL, -- Comma-separated tags
    created_by INTEGER NOT NULL,
    ai_explanation TEXT, -- JSON cached string
    status VARCHAR(50) DEFAULT 'Planning', -- Planning, In Progress, Review, Completed, Blocked
    health_score VARCHAR(50) DEFAULT 'Green', -- Green, Yellow, Red
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
);

-- 4. Assignments Table (Project Members)
CREATE TABLE assignments (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    match_score REAL NOT NULL,
    role VARCHAR(150), -- Specific role in the project
    utilization INTEGER DEFAULT 0, -- Utilization percentage (0-100)
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE
);

-- 5. Tasks Table
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id INTEGER, -- Can be null if unassigned
    status VARCHAR(50) DEFAULT 'To Do', -- To Do, In Progress, Review, Blocked, Completed
    priority VARCHAR(50) DEFAULT 'Medium', -- Low, Medium, High
    due_date TIMESTAMP,
    story_points INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (assignee_id) REFERENCES employees (id) ON DELETE SET NULL
);

-- 6. Milestones Table
CREATE TABLE milestones (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'Pending', -- Pending, Completed, Overdue
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);
