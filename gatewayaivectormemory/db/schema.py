INIT_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    scope TEXT NOT NULL DEFAULT 'project',
    source TEXT NOT NULL DEFAULT 'manual',
    project_dir TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT '',
    session_id INTEGER NOT NULL DEFAULT 0,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT 'manual',
    user_id TEXT NOT NULL DEFAULT '',
    session_id INTEGER NOT NULL DEFAULT 0,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS team_memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT 'manual',
    project_dir TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    session_id INTEGER NOT NULL DEFAULT 0,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session_state (
    id SERIAL PRIMARY KEY,
    project_dir TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT '',
    is_blocked BOOLEAN NOT NULL DEFAULT false,
    block_reason TEXT NOT NULL DEFAULT '',
    next_step TEXT NOT NULL DEFAULT '',
    current_task TEXT NOT NULL DEFAULT '',
    progress TEXT NOT NULL DEFAULT '[]',
    recent_changes TEXT NOT NULL DEFAULT '[]',
    pending TEXT NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_session_id INTEGER NOT NULL DEFAULT 0,
    UNIQUE(project_dir, user_id)
);

CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    project_dir TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT '',
    issue_number INTEGER NOT NULL,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    content TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    investigation TEXT NOT NULL DEFAULT '',
    root_cause TEXT NOT NULL DEFAULT '',
    solution TEXT NOT NULL DEFAULT '',
    files_changed TEXT NOT NULL DEFAULT '[]',
    test_result TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    feature_id TEXT NOT NULL DEFAULT '',
    parent_id INTEGER NOT NULL DEFAULT 0,
    memory_id TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS issues_archive (
    id SERIAL PRIMARY KEY,
    project_dir TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT '',
    issue_number INTEGER NOT NULL,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    investigation TEXT NOT NULL DEFAULT '',
    root_cause TEXT NOT NULL DEFAULT '',
    solution TEXT NOT NULL DEFAULT '',
    files_changed TEXT NOT NULL DEFAULT '[]',
    test_result TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    feature_id TEXT NOT NULL DEFAULT '',
    parent_id INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT '',
    original_issue_id INTEGER NOT NULL DEFAULT 0,
    memory_id TEXT NOT NULL DEFAULT '',
    archived_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    project_dir TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT '',
    feature_id TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    sort_order INTEGER NOT NULL DEFAULT 0,
    parent_id INTEGER NOT NULL DEFAULT 0,
    task_type TEXT NOT NULL DEFAULT 'manual',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tasks_archive (
    id SERIAL PRIMARY KEY,
    project_dir TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT '',
    feature_id TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    sort_order INTEGER NOT NULL DEFAULT 0,
    parent_id INTEGER NOT NULL DEFAULT 0,
    task_type TEXT NOT NULL DEFAULT 'manual',
    metadata TEXT NOT NULL DEFAULT '{}',
    original_task_id INTEGER NOT NULL DEFAULT 0,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_dir);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags);
CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source);
CREATE INDEX IF NOT EXISTS idx_user_memories_user ON user_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_tags ON user_memories(tags);
CREATE INDEX IF NOT EXISTS idx_team_memories_project ON team_memories(project_dir);
CREATE INDEX IF NOT EXISTS idx_team_memories_tags ON team_memories(tags);
CREATE INDEX IF NOT EXISTS idx_issues_project ON issues(project_dir);
CREATE INDEX IF NOT EXISTS idx_issues_user ON issues(user_id);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_date ON issues(date);
CREATE INDEX IF NOT EXISTS idx_issues_archive_project ON issues_archive(project_dir);
CREATE INDEX IF NOT EXISTS idx_issues_archive_user ON issues_archive(user_id);
CREATE INDEX IF NOT EXISTS idx_issues_archive_date ON issues_archive(date);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_dir);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_feature ON tasks(feature_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_archive_project ON tasks_archive(project_dir);
CREATE INDEX IF NOT EXISTS idx_tasks_archive_user ON tasks_archive(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_archive_feature ON tasks_archive(feature_id);
"""


def init_db(conn):
    conn.execute(INIT_SQL)
    conn.execute(INDEXES_SQL)
    conn.commit()
