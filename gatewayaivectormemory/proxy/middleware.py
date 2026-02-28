"""Request logging middleware - integrated into app.py via @app.middleware("http").

The log_requests middleware in proxy/app.py records:
- user_id (from X-User-Id header)
- project_dir (from X-Project-Dir header)
- tool (request path)
- latency (ms)

This module is reserved for future middleware extensions (auth, rate limiting, etc).
"""
