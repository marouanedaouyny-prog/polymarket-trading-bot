# GAPS

1. Which commands are authoritative? Verify against CI, pyproject, pytest.ini, Dockerfile, and executable entrypoints.
2. Which modules form the actual runtime path amid duplicate/legacy files? Trace imports from entrypoints and API routers.
3. What trading invariants must future agents preserve? Inspect config, order execution, API startup, and readiness gate.
4. Are foreign agent configs available? Check existence only; do not read them.
