-- Dev seed: sample STIRT namespace, machines, and process definitions
-- Run after: uv run alembic upgrade head

INSERT INTO namespaces (id, name, description) VALUES
    ('00000000-0000-0000-0000-000000000001', 'STIRT', 'Short Term Interest Rate Trading'),
    ('00000000-0000-0000-0000-000000000002', 'SPOT', 'Spot FX Trading')
ON CONFLICT (name) DO NOTHING;

INSERT INTO machines (id, namespace_id, hostname, description) VALUES
    ('00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0000-000000000001', 'server1.stirt.internal', 'Primary STIRT server'),
    ('00000000-0000-0000-0001-000000000002', '00000000-0000-0000-0000-000000000001', 'server2.stirt.internal', 'Secondary STIRT server')
ON CONFLICT DO NOTHING;

INSERT INTO process_definitions (id, name, description, example_qa) VALUES
    ('00000000-0000-0000-0002-000000000001', 'CurveBuilder',
     'Builds yield curves from market data each morning',
     '[{"question": "Is curve building complete?", "answer": "Curve building completed at 14:23."}]'),
    ('00000000-0000-0000-0002-000000000002', 'RiskEngine',
     'Computes real-time P&L and risk metrics',
     '[{"question": "Is risk engine running?", "answer": "Risk engine is processing, last update 30s ago."}]'),
    ('00000000-0000-0000-0002-000000000003', 'HeadlineProcessor',
     'Processes financial news headlines for trading signals',
     '[{"question": "Are headlines being processed?", "answer": "Headline processor running, 142 headlines today."}]')
ON CONFLICT (name) DO NOTHING;

INSERT INTO machine_processes (id, machine_id, process_definition_id, log_paths) VALUES
    ('00000000-0000-0000-0003-000000000001', '00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0002-000000000001', '["/opt/curve/logs/*.log"]'),
    ('00000000-0000-0000-0003-000000000002', '00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0002-000000000002', '["/opt/risk/logs/*.log"]'),
    ('00000000-0000-0000-0003-000000000003', '00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0002-000000000003', '["/opt/hl/logs/*.log"]'),
    ('00000000-0000-0000-0003-000000000004', '00000000-0000-0000-0001-000000000002', '00000000-0000-0000-0002-000000000001', '["/opt/curve/logs/*.log"]')
ON CONFLICT DO NOTHING;
