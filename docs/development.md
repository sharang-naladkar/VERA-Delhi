# VERA Development Guide

## Local Setup & Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose

## Quickstart

### 1. Environment Setup
```bash
cp .env.example .env
```

### 2. Backend Local Execution
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r services/api/requirements-dev.txt
uvicorn app.main:app --app-dir services/api --reload --port 8000
```

### 3. Frontend Local Execution
```bash
cd frontend
npm install
npm run dev
```

### 4. Running Backend Tests
```bash
pytest services/api/tests -v
```

### 5. Running Frontend Tests
```bash
cd frontend
npm run test
```

### 6. Linting & Formatting
```bash
ruff check services/api
cd frontend && npm run lint
```
