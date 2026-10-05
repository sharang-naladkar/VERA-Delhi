# VERA Architecture Specification

## 1. System Overview

VERA is an autonomous, agentic AI investment-fraud investigation platform designed to ingest multi-modal digital artifacts (transcripts, screenshots, voice notes, videos, URLs, APKs, payment handles) and perform forensic analysis across regulatory, forensic, and behavioral dimensions.

```
                         VERA System Topology (Phase 01)
                         
             ┌─────────────────────────────────────────┐
             │       Frontend: React + Vite + TS       │
             └────────────────────┬────────────────────┘
                                  │ OpenAPI REST Contract
             ┌────────────────────▼────────────────────┐
             │            FastAPI Backend              │
             │   (Centralized Errors, Request Tracing) │
             └────────┬───────────┬───────────┬────────┘
                      │           │           │
          ┌───────────▼──┐  ┌─────▼─────┐  ┌──▼──────────┐
          │  PostgreSQL  │  │   Redis   │  │    MinIO    │
          │  (Metadata)  │  │ (Queues)  │  │  (Storage)  │
          └──────────────┘  └───────────┘  └─────────────┘
```

## 2. Core Architecture Principles

1. **Modular Provider Isolation**: All analysis capabilities (LLMs, OCR, STT, Deepfake CV, URL classifier, APK classifier, Embedding) sit behind standardized interfaces. Providers can be swapped seamlessly without touching orchestrator or business logic.
2. **Frontend Independence**: The backend exposes purely OpenAPI-compliant REST APIs and schema definitions. No React or presentation assumptions exist in backend code.
3. **Model Independence**: Model names and endpoints are managed strictly via environment configuration and provider protocols.
4. **Evidence-First Architecture**: Standardized `EvidenceContract` instances capture findings, source details, severity, confidence, and raw payloads.
5. **Fail-Safe Operation**: Missing or failing services return explicit `UNAVAILABLE` or `FAILED` statuses, never fabricating safe or false-positive verdicts.
