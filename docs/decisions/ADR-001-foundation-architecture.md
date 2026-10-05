# ADR-001: Foundation Architecture, Technology Stack & Fail-Safe Principles

## Status
Accepted

## Context
VERA (Verification, Evidence, Risk & Analysis) is an autonomous, agentic AI platform designed to investigate complex investment and trading fraud schemes across India. The platform requires high modularity, support for multi-modal ingestion (images, audio, video, APKs, domains, payment IDs), seamless provider hot-swapping, strict fail-safe behavior, and decoupled frontend/backend infrastructure.

## Decisions

### 1. Backend: Python 3.12+ with FastAPI & SQLAlchemy
- **Rationale**: Python is the lingua franca for AI orchestration, machine learning inference, computer vision, and NLP pipelines. FastAPI provides high-performance asynchronous I/O, native Pydantic schema validation, and automatic OpenAPI contract generation. SQLAlchemy 2.0 with Alembic gives type-safe relational modeling and migration management.

### 2. Frontend: React + TypeScript + Vite + Tailwind CSS
- **Rationale**: Strict separation of concerns between presentation and domain logic. React with TypeScript provides type safety aligned with OpenAPI schemas. Vite enables ultra-fast compilation without the server-side coupling of SSR frameworks. All communications go through a dedicated API client layer (`src/api/`).

### 3. Database: PostgreSQL
- **Rationale**: Robust ACID relational storage for investigation records, audit logs, and entity relationship graphs. Ready for native vector search (`pgvector`) in subsequent RAG phases.

### 4. Cache & Task Queues: Redis
- **Rationale**: Lightweight, fast in-memory key-value store for session caching, rate limiting, and future task worker queue brokering.

### 5. Object Storage: MinIO
- **Rationale**: S3-compatible, high-performance object storage suitable for self-hosted local deployments as well as cloud portability for storing raw media evidence, forensic captures, APK binaries, and generated reports.

### 6. Provider Interfaces with Fail-Safe Placeholders
- **Rationale**: To prevent tight coupling to any single LLM or ML library (e.g. Ollama, OpenAI, MesoNet, Tesseract), all intelligence layers implement abstract interfaces (`BaseProvider`, `LLMProvider`, `OCRProvider`, `STTProvider`, etc.). In Phase 01, `Unavailable*` implementations are registered to guarantee that unconfigured or failing components return structured `UNAVAILABLE` statuses rather than fabricating false-safe verdicts.

### 7. Evidence-First Architecture
- **Rationale**: All future analyzers emit standardized `EvidenceContract` instances with severity, confidence, source metadata, and execution status (`SUCCESS`, `PARTIAL`, `FAILED`, `UNAVAILABLE`).

## Consequences
- Clean modular boundaries prevent cascade failures.
- Frontend and backend can be refactored or swapped independently.
- Subsystem health can be probed continuously via `/health/ready`.
