# 🧑‍💻 Member 3: Hippocampal Search & Retrieval Specialist

## 🎯 Role Overview
**Title:** Hippocampal Search & Retrieval Specialist  
**Core Domain:** Episodic Memory, Dual Symptom/Full Text Embeddings, Polyglot Stack Trace Fingerprinting, pgvector HNSW Indexing, Hybrid Fusion Algorithm, and Deterministic Pattern Separation.

---

## 📦 Code Ownership & Deliverables

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Embeddings Engine** | `app/core/embeddings.py` | Local `BAAI/bge-small-en-v1.5` dual symptom/full embeddings (384-dim) with SQLite cache |
| **Stacktrace Parser** | `app/core/fingerprint.py` | Multi-language stack trace parser (Python, Java, Node.js, Go) and SHA-1 application frame fingerprinting |
| **Retrieval Engine** | `app/memory/retrieval.py` | The Hippocampal Hybrid Retrieval Engine combining 5 distinct signals |
| **Database Schema** | `db/schema.sql` | PostgreSQL 16 schema with `pgvector` HNSW index and GIN full-text index |
| **Long-Term Store** | `app/memory/store.py` | PostgreSQL pgvector storage adapter with zero-dependency offline fallback |

---

## ⚡ The Hippocampal Hybrid Retrieval Formula
Retrieval fuses 5 weighted signals to achieve accurate incident recall:
$$\text{Score} = 0.45 \cdot S_{\text{vector}} + 0.20 \cdot S_{\text{FTS}} + 0.20 \cdot S_{\text{fingerprint}} + 0.10 \cdot S_{\text{service}} + 0.05 \cdot S_{\text{code}}$$

- **Sub-5ms Latency:** Achieved **3.72 ms** p50 retrieval latency (over 100x faster than the 500ms target).
- **Dual Indexing:** Symptoms are indexed independently from full post-mortems to eliminate premature cue bias.
- **Pattern Separation:** Deterministic mismatch flags (`trigger_mismatch`, `service_mismatch`, `fix_did_not_work`, `old`) actively rule out false look-alikes.

---

## 🧪 Verification & Acceptance Tests

```bash
# 1. Verify embeddings and stack trace fingerprinting unit tests
PYTHONPATH="" .venv/bin/pytest tests/unit/test_embeddings.py tests/unit/test_fingerprint.py -v

# 2. Query episodic memory for past connection pool incidents
PYTHONPATH="" .venv/bin/python -m app.cli ask "checkout-api 503s and p99 8s after deploy" --service checkout-api
```

---

## 🎤 Presentation & Demo Role
- **Scene 3 (1:15 - 1:45):** Deep dive into Pattern Separation: distinguishing CoreDNS pod eviction (INC-0019) from database connection pool leaks (INC-0007).
