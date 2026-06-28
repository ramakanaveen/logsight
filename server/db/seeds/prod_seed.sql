-- Prod seed: namespace baseline only — no test data or sample processes
-- Run after: LOGSIGHT_ENV=prod uv run alembic upgrade head

-- Insert your production namespaces here
-- INSERT INTO namespaces (id, name, description) VALUES (...);

-- Machines and processes are registered at deploy time
-- via sidecar self-registration and admin UI
