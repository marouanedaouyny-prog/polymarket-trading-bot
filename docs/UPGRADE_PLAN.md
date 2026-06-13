# Polymarket AI Trading System - Upgrade Plan

## Overview
Current Rating: 7.5/10 - Core functionality works, needs production hardening

---

## Phase 1: Code Quality (Priority: HIGH)

### 1.1 Type Checking with MyPy
```
Task: Add type hints and run mypy
- Install: pip install mypy
- Run: mypy . --ignore-missing-imports
- Fix all type errors
- Add pyproject.toml with mypy config
```

### 1.2 Linting with Flake8
```
Task: Enforce code style
- Install: pip install flake8
- Run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
- Add .flake8 config file
- Fix all linting errors
```

### 1.3 Add Type Hints
```
Files to update with type hints:
- src/data/*.py
- src/trading/*.py
- src/risk/*.py
- src/ml/*.py
- src/portfolio/*.py
- src/execution/*.py
```

---

## Phase 2: Docker & Deployment (Priority: HIGH)

### 2.1 Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "src.polymarket_bot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 Create docker-compose.yml
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - config/.env
    volumes:
      - ./data:/app/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### 2.3 Add .dockerignore
```
__pycache__
*.pyc
.git
node_modules
venv/
*.md
```

---

## Phase 3: CI/CD Pipeline (Priority: HIGH)

### 3.1 Create GitHub Actions Workflow
File: `.github/workflows/ci.yml`
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install mypy flake8 pytest pytest-cov

      - name: Run MyPy
        run: mypy . --ignore-missing-imports

      - name: Run Flake8
        run: flake8 . --count --select=E9,F63,F7,F82

      - name: Run Tests
        run: pytest --cov=src --cov-report=xml
```

### 3.2 Add pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

---

## Phase 4: Security Enhancements (Priority: MEDIUM)

### 4.1 Verify FastAPI API Key Protection
```
Task: Ensure all endpoints require API key
- Check main.py for @app.middleware("http")
- Verify _require_api_key dependency on sensitive endpoints
- Test with curl:
  curl -H "X-API-Key: wrong" http://localhost:8000/markets
  Should return 401/403
```

### 4.2 Environment Variables Validation
```
Task: Validate required env vars on startup
- Add validation in src/utils/config.py
- Fail fast if POLYMARKET_API_KEY missing
- Log warning if optional vars missing
```

### 4.3 Add Rate Limiting
```
Task: Prevent API abuse
- Install: pip install slowapi
- Add rate limiter to FastAPI
- 100 req/min for authenticated users
- 20 req/min for unauthenticated
```

---

## Phase 5: Documentation (Priority: MEDIUM)

### 5.1 Create Comprehensive README.md
```
Sections:
- Quick Start (5 min)
- Configuration
- Running locally
- Docker deployment
- Testing
- Architecture diagram
- API endpoints
- Troubleshooting
```

### 5.2 Add API Documentation
```
Task: OpenAPI/Swagger docs
- Already available at /docs
- Add proper descriptions to all endpoints
- Add example requests/responses
```

---

## Phase 6: Production Enhancements (Priority: LOW)

### 6.1 Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### 6.2 Graceful Shutdown
```
Task: Handle SIGTERM properly
- Close DB connections
- Cancel pending orders
- Flush logs
```

### 6.3 Metrics Export (Prometheus)
```
Task: Add Prometheus metrics
- Request count
- Response time
- Error rate
- Active trades count
```

---

## Execution Order

```
Week 1:
- Day 1-2: Run mypy, fix errors
- Day 3-4: Run flake8, fix errors
- Day 5: Add type hints to core modules

Week 2:
- Day 1-2: Create Dockerfile
- Day 3-4: Create docker-compose.yml
- Day 5: Test Docker build

Week 3:
- Day 1-2: Create GitHub Actions workflow
- Day 3-4: Add pytest.ini, run full test suite
- Day 5: Verify CI pipeline works

Week 4:
- Day 1-2: Verify FastAPI security
- Day 3-4: Update README
- Day 5: Health check endpoint
```

---

## Quick Win Commands

```bash
# Install dev dependencies
pip install mypy flake8 pytest pytest-cov slowapi

# Run type check
mypy . --ignore-missing-imports

# Run linting
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Build Docker
docker build -t polymarket-bot .

# Run with Docker Compose
docker-compose up -d
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage | 80% | 90% |
| Type Hints | Partial | 100% |
| Lint Errors | Unknown | 0 |
| Docker Ready | No | Yes |
| CI Pipeline | No | Yes |
| Documentation | Scattered | Unified |