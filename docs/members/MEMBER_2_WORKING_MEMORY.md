# 🧑‍💻 Member 2: Working Memory & Ingestion Engineer

## 🎯 Role Overview
**Title:** Working Memory & Ingestion Engineer  
**Core Domain:** Prefrontal Cortex (Redis Working Memory), Zero-Leak Secret Scrubbing, Error & Telemetry Normalization, and Multi-Format Ingestion Pipeline.

---

## 📦 Code Ownership & Deliverables

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Working Memory** | `app/memory/working.py` | Redis live context store (`inc:{id}:meta`, `events`, `services`, `hypotheses`) with 72-hour TTL expiration |
| **Secret Redaction** | `app/core/redact.py` | High-security regex scrubbers eliminating AWS keys, GitHub tokens, Slack tokens, JWTs, passwords, and PII |
| **Normalization** | `app/core/normalize.py` | Timestamp, UUID, IP address abstraction while preserving HTTP status codes (`HTTP/1.1 502`) |
| **Multi-Format Loaders**| `app/ingestion/loaders.py` | Parsers for Post-mortems (Markdown), Jira JSON, and Slack conversation transcripts |
| **Structuring Heuristics**| `app/ingestion/extract.py`| Metadata, symptom, and root cause extraction |
| **Ingestion Pipeline** | `app/ingestion/pipeline.py` | SHA-256 deduplication and near-duplicate cosine similarity detection ($\ge 0.97$) |
| **Dataset Generation** | `data/seed/`, `scripts/generate_seed_data.py` | 64 synthetic incident files, ground-truth labels, and runbook pairings |

---

## 🛡️ Key Architectural Guardrails
1. **Zero Secret Leakage Guarantee**:
   - Every incoming alert, stack trace, and slack log is scrubbed *before* entering working memory or LLM context.
2. **Deterministic Redis TTL**:
   - Active working context expires automatically after 72 hours, preventing working memory bloat.
3. **Idempotent Ingestion**:
   - SHA-256 hashing and vector similarity thresholds prevent duplicate entries across concurrent incident ingestion.

---

## 🧪 Verification & Acceptance Tests

```bash
# 1. Verify redaction and normalization unit tests
PYTHONPATH="" .venv/bin/pytest tests/unit/test_redact.py tests/unit/test_normalize.py -v

# 2. Seed memory and run multi-format document ingestion
PYTHONPATH="" .venv/bin/python -m app.cli seed
PYTHONPATH="" .venv/bin/python -m app.cli ingest data/seed
```

---

## 🎤 Presentation & Demo Role
- **Scene 2 Co-presenter (0:35 - 1:15):** Explaining how Redis working memory captures incoming alerts, normalizes error text, and manages the live incident timeline.
