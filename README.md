# VERA — Autonomous Agentic AI Investment Fraud Investigation Platform

VERA is an autonomous, agentic AI platform engineered to detect, deconstruct, and investigate digital investment fraud, fake SEBI-registered advisory networks, fraudulent trading applications, and multi-channel financial scams. By correlating multi-modal artifacts (voice notes, deepfake video claims, manipulated trade screenshots, malicious APKs, phishing domains, and payment handles) across regulatory registries and deterministic risk models, VERA provides verifiable, evidence-backed forensic reports.

---

## Current Status

```text
Phase 01 — Foundation
Status: Complete
```

*Phase 01 establishes repository architecture, replaceable provider interfaces, OpenAPI and JSON Schema contracts, fail-safe status modeling, PostgreSQL/Alembic database foundations, MinIO object storage, Redis caching, and automated CI pipelines.*

---

## Architecture

```text
                         VERA System Architecture
                         
                 ┌──────────────────────────────────────┐
                 │       React + TypeScript + Vite      │
                 └──────────────────┬───────────────────┘
                                    │ OpenAPI REST
                 ┌──────────────────▼───────────────────┐
                 │           FastAPI Backend            │
                 │   (Logging, Errors, UUID Tracing)    │
                 └───────┬──────────┬──────────┬────────┘
                         │          │          │
             ┌───────────▼──┐ ┌─────▼─────┐ ┌──▼───────────┐
             │  PostgreSQL  │ │   Redis   │ │    MinIO     │
             │  (Metadata)  │ │ (Queues)  │ │  (Storage)   │
             └──────────────┘ └───────────┘ └──────────────┘
                         │
        ┌────────────────┼────────────────────────┐
        ▼                ▼                        ▼
  LLM Providers    Forensic Analyzers       Tool Verifiers
 (Pluggable ABC)  (OCR/STT/MesoNet/APK)     (SEBI/WHOIS/UPI)
```

---

## Technology Stack

- **Backend API**: Python 3.12+, FastAPI, Uvicorn, Pydantic v2
- **Database & ORM**: PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic migrations
- **Cache & Jobs**: Redis 7
- **Object Storage**: MinIO (S3-compatible)
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons
- **Testing & Quality**: Pytest, Vitest, Testing Library, Ruff, ESLint
- **Containerization & CI**: Docker, Docker Compose, GitHub Actions

---

## Repository Structure

```text
VERA/
├── frontend/             # React + Vite + TypeScript application
│   ├── src/
│   │   ├── api/          # Pure API client layer
│   │   ├── components/   # UI components
│   │   ├── hooks/        # React hooks
│   │   ├── pages/        # Route views (Home, Investigation)
│   │   └── types/        # TypeScript interfaces & contracts
│   └── tests/            # Vitest unit & component tests
│
├── services/
│   └── api/              # FastAPI backend service
│       ├── app/
│       │   ├── api/      # REST route handlers & dependencies
│       │   ├── core/     # Configuration, logging, centralized errors
│       │   ├── contracts/# Pydantic schemas (Evidence, Status, Investigation)
│       │   ├── db/       # SQLAlchemy models & Alembic migrations
│       │   ├── providers/# Pluggable interfaces (LLM, OCR, STT, Deepfake, URL, APK)
│       │   └── services/ # Business logic & readiness probes
│       └── tests/        # Pytest test suite
│
├── contracts/            # OpenAPI spec & standardized JSON schemas
│   ├── openapi.yaml
│   └── schemas/          # investigation, evidence, input, entity, claim, risk, report
│
├── infra/docker/         # Production & development Dockerfiles
├── docs/                 # Architecture documents & ADRs
└── docker-compose.yml    # Full local multi-service orchestrator
```

---

## Local Setup & Quickstart

### 1. Clone & Configure Environment

```bash
cp .env.example .env
```

### 2. Run Entire Stack with Docker Compose

```bash
docker compose up --build
```

Services will be accessible at:
- **Frontend Web UI**: `http://localhost:5173`
- **FastAPI Documentation**: `http://localhost:8000/docs`
- **FastAPI OpenAPI Schema**: `http://localhost:8000/openapi.json`
- **MinIO Console**: `http://localhost:9001` (Credentials in `.env.example`)

---

## Running Locally Without Docker

### Backend API
```bash
# Set up Python virtual environment
python -m venv .venv
# Activate virtual environment:
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r services/api/requirements-dev.txt

# Run FastAPI server
uvicorn app.main:app --app-dir services/api --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Testing & Quality Assurance

### Run Backend Tests & Coverage
```bash
pytest services/api/tests -v
```

### Run Python Linting
```bash
ruff check services/api
```

### Run Frontend Tests
```bash
cd frontend
npm run test
```

### Run Frontend Build
```bash
cd frontend
npm run build
```

---

## Core API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Basic liveness probe |
| `GET` | `/health/ready` | Readiness probe (validates PostgreSQL, Redis, MinIO) |
| `POST` | `/v1/investigations` | Initializes a new fraud investigation |
| `GET` | `/v1/investigations/{id}` | Retrieves investigation details and status |

---

## Critical Architecture Guarantees

1. **Fail-Safe Integrity**: If an analyzer backend (LLM, OCR, STT, Deepfake) is unconfigured or fails, it explicitly returns `UNAVAILABLE` or `FAILED`. It **never** fabricates a false-safe verdict.
2. **Provider Replaceability**: Swapping local models (e.g. Qwen3) with remote providers or updating OCR/CV models requires implementing the provider interface without changing core business logic.
3. **Decoupled Client**: The frontend interacts exclusively via OpenAPI REST contracts, enabling complete client replacement if required.
