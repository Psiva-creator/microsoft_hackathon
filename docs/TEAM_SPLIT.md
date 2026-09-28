# 👥 6-Member Team Delegation & Work Breakdown

**Project Name:** Incident Response Agent with Brain-Inspired Memory  
**Event:** Hack With Hyderabad 3.0 / Devnovate Hackathon  
**Submission Date:** Tomorrow (Final Submission)

---

## 🎯 Executive Summary & Team Structure

This project applies cognitive memory architectures (Prefrontal Cortex, Hippocampus, Neocortex, Consolidation, and Procedural Memory) to autonomous on-call incident response and proactive code risk analysis.

The engineering effort is divided across **6 specialized roles** to ensure end-to-end execution, high test coverage, deterministic safety, rigorous ablation benchmarking, and a presentation.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MEMBER 1: TEAM LEAD & ARCHITECT                 │
│         (System Architecture, Core Guardrails, CLI Orchestration)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│   MEMBER 2   │             │   MEMBER 3   │             │   MEMBER 4   │
│   WORKING    │             │ HIPPOCAMPAL  │             │  REASONING   │
│   MEMORY &   │             │   SEARCH &   │             │   AGENT &    │
│  INGESTION   │             │  RETRIEVAL   │             │  READ-ONLY   │
│  (Redis/FTS) │             │ (pgvector)   │             │   ADAPTERS   │
└──────────────┘             └──────────────┘             └──────────────┘
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    │
       ┌────────────────────────────┴────────────────────────────┐
       ▼                                                         ▼
┌──────────────────────────────┐          ┌──────────────────────────────┐
│           MEMBER 5           │          │           MEMBER 6           │
│   EVALUATION, BENCHMARKING   │          │    INTERFACES, SLACK BOT,    │
│    & CONTINUOUS LEARNING     │          │    REST API & DEVREL LEAD    │
│   (Ablation / Consolidation) │          │  (Bolt / FastAPI / PR-Check) │
└──────────────────────────────┘          └──────────────────────────────┘
```

---

## 🧑‍💻 Member 1: Team Lead & Systems Architect

### Primary Role
**System Orchestration, Core Guardrails & CLI**

### Code Ownership
- [app/config.py](../app/config.py): Centralized environment settings (`pydantic-settings`).
- [app/logging.py](../app/logging.py): Structured JSON and console logging (`structlog`).
- [app/models.py](../app/models.py): Canonical domain schemas (`Cue`, `Analysis`, `Hypothesis`, `ScoredIncident`, `LiveContext`).
- [app/cli.py](../app/cli.py): Unified rich terminal CLI (`seed`, `ingest`, `ask`, `investigate`, `resolve`, `pr-check`, `consolidate`, `stats`, `eval`).
- [docs/DECISIONS.md](DECISIONS.md): Architectural Decision Records (ADRs).

### Key Responsibilities & Deliverables
1. **Safety Enforcement:** Enforced strict read-only guarantees across all tools (`ALLOW_ACTIONS=false`).
2. **Domain Modeling:** Designed unified Pydantic v2 schemas shared across API, CLI, Agent, and DB.
3. **CLI Experience:** Built rich terminal output with color-coded confidence badges, evidence tables, and runbook suggestions.
4. **Project Scaffolding:** Configured [pyproject.toml](../pyproject.toml), [docker-compose.yml](../docker-compose.yml), and [Makefile](../Makefile).

### Verification & Testing Commands
```bash
.venv/bin/pytest tests/unit/test_scaffold.py tests/unit/test_tools_readonly.py
.venv/bin/ruff check .
cli --help
cli stats
```

### Video & Presentation Speaking Part
- **Scene 1 (0:00 - 0:35):** Introduction, the 3 AM on-call crisis, and the Brain-Inspired Memory vision.
- **Scene 6 (2:45 - 3:00):** Closing statement, production safety, and submission wrap-up.

---

## 🧑‍💻 Member 2: Working Memory & Ingestion Engineer

### Primary Role
**Prefrontal Cortex (Redis) & Raw Document Ingestion Pipelines**

### Code Ownership
- [app/memory/working.py](../app/memory/working.py): Redis live context (`inc:{id}:meta`, `events`, `services`, `hypotheses`) with 72-hour TTL expiration.
- [app/core/redact.py](../app/core/redact.py): Zero-leak secret scrubbing (AWS keys, GitHub tokens, Slack tokens, JWTs, Bearer credentials, passwords, PII).
- [app/core/normalize.py](../app/core/normalize.py): Timestamp, UUID, IP address, and numerical abstraction while preserving HTTP status codes (`HTTP/1.1 502`).
- [app/ingestion/loaders.py](../app/ingestion/loaders.py): Multiformat ingestion (Post-mortems, Jira JSON, Slack conversation logs).
- [app/ingestion/extract.py](../app/ingestion/extract.py): Heuristic and LLM-assisted incident structuring.
- [app/ingestion/pipeline.py](../app/ingestion/pipeline.py): End-to-end ingestion pipeline with SHA-256 deduplication and near-duplicate detection ($\ge 0.97$).

### Key Responsibilities & Deliverables
1. **Working Memory Lifecyle:** Redis context store retaining live investigation timeline with graceful in-memory fallback.
2. **Data Ingestion:** Processed 64 diverse incident documents across markdown, Jira JSON, and Slack transcripts.
3. **Data Protection:** Implemented regex scrubbing ensuring zero secret or credential leakage in prompt context or memory.
4. **Idempotency:** SHA-256 and cosine deduplication preventing duplicate incident ingestion.

### Verification & Testing Commands
```bash
.venv/bin/pytest tests/unit/test_redact.py tests/unit/test_normalize.py
cli seed
cli ingest data/seed
```

### Video & Presentation Speaking Part
- **Scene 2 Co-presenter (0:35 - 1:15):** Explaining how Redis working memory captures incoming alerts, normalizes error text, and manages the live incident timeline.

---

## 🧑‍💻 Member 3: Hippocampal Search & Retrieval Specialist

### Primary Role
**Episodic Memory, Hybrid Vector/FTS Retrieval & Pattern Separation**

### Code Ownership
- [app/core/embeddings.py](../app/core/embeddings.py): Dual symptom/full text embeddings via `BAAI/bge-small-en-v1.5` (384-dim) with persistent SQLite cache.
- [app/core/fingerprint.py](../app/core/fingerprint.py): Multi-language stack trace parser (Python, Java, Node.js, Go) and SHA-1 application frame fingerprinting.
- [app/memory/retrieval.py](../app/memory/retrieval.py): The Hippocampal Retrieval Engine combining Vector ($W=0.45$), FTS ($W=0.20$), Fingerprints ($W=0.20$), Service Graph ($W=0.10$), and Code History ($W=0.05$).
- [db/schema.sql](../db/schema.sql): PostgreSQL 16 schema with `pgvector` HNSW index and GIN full-text index.

### Key Responsibilities & Deliverables
1. **Sub-5ms Recall:** Achieved **3.72 ms** p50 retrieval latency (over 100x faster than the 500ms target).
2. **Dual Representation:** Indexed symptoms separately from full post-mortems to eliminate premature cue bias.
3. **Pattern Separation:** Built deterministic mismatch flags (`trigger_mismatch`, `service_mismatch`, `fix_did_not_work`, `old`) to rule out false look-alikes.
4. **Resilience:** Implemented zero-dependency offline fallback ensuring high fidelity retrieval even when Postgres is detached.

### Verification & Testing Commands
```bash
.venv/bin/pytest tests/unit/test_embeddings.py tests/unit/test_fingerprint.py
cli ask "checkout-api 503s and p99 8s after deploy" --service checkout-api
```

### Video & Presentation Speaking Part
- **Scene 3 (1:15 - 1:45):** Deep dive into Pattern Separation: distinguishing CoreDNS pod eviction (INC-0019) from database connection pool leaks (INC-0007).

---

## 🧑‍💻 Member 4: Reasoning Agent & Tooling Developer

### Primary Role
**Claude Agent Reasoning Loop, Read-Only Tooling & Adapters**

### Code Ownership
- [app/agent/investigate.py](../app/agent/investigate.py): ReAct reasoning loop, hypothesis formulation, evidence extraction, citation validation, and confidence capping.
- [app/agent/tools.py](../app/agent/tools.py): 9 read-only tool definitions with safety dispatch guards.
- [app/adapters/base.py](../app/adapters/base.py): Abstract interfaces for telemetry and infra query adapters.
- [app/adapters/mock.py](../app/adapters/mock.py): High-fidelity mock adapters for logs, metrics, deploys, and service topology.
- [data/mock_env/scenarios/](../data/mock_env/scenarios/): Outage scenarios A (pool leak), B (cert expiry), C (novel error), and D (DNS look-alike).

### Key Responsibilities & Deliverables
1. **Deterministic Confidence Rules:** Capped confidence to `low` when strong mismatch flags exist, `none` precedent forces `low`, and zero citations trigger auto-downgrades.
2. **Citation Integrity (0 Hallucinations):** Automatic validation ensuring every cited precedent exists in memory; invalid IDs are stripped into `dropped_citations`.
3. **Read-Only Safety Guarantee:** Zero autonomous mutating commands. Remediation actions (rollbacks, restarts) are surfaced exclusively under `needs_human_decision`.
4. **ReAct Orchestration:** Coordinated evidence gathering across `query_logs`, `query_metrics`, `get_recent_deploys`, `get_service_dependencies`, and `find_code_history`.

### Verification & Testing Commands
```bash
.venv/bin/pytest tests/unit/test_agent_scenarios.py tests/unit/test_confidence_rules.py
cli investigate --scenario A_pool_exhaustion
cli investigate --scenario C_novel_error
```

### Video & Presentation Speaking Part
- **Scene 2 (0:35 - 1:15):** Live terminal walkthrough of Scenario A: alert arrival, tool queries to logs/metrics, and evidence-cited analysis generation.

---

## 🧑‍💻 Member 5: Evaluation & Continuous Learning Lead

### Primary Role
**Ablation Benchmark, Sleep-Replay Consolidation & Post-Mortem Engine**

### Code Ownership
- [app/eval/harness.py](../app/eval/harness.py): Multi-mode leave-one-out evaluation suite (Recall@1, Recall@3, Recall@5, MRR, Latency).
- [eval/cases.jsonl](../eval/cases.jsonl): 60 leave-one-out benchmark test cases.
- [app/jobs/consolidate.py](../app/jobs/consolidate.py): Nightly sleep-replay consolidation with Agglomerative Clustering and half-life decay.
- [app/agent/postmortem.py](../app/agent/postmortem.py): Resolution capture, post-mortem generation, and memory write-back.
- [app/memory/stats.py](../app/memory/stats.py): Laplace-smoothed runbook success probabilities: $p = \frac{s + 1}{s + f + 2}$.

### Key Responsibilities & Deliverables
1. **Quantitative Proof:** Proved that Hybrid Retrieval significantly outperforms Keyword-only and Vector-only search across 60 evaluation cases.
2. **Report Generation:** Automated generation of [eval/report.md](../eval/report.md) and [eval/report.json](../eval/report.json).
3. **Sleep-Replay Consolidation:** Clustered related outages into general `patterns`, synthesized preventive rules, and decayed weights of obsolete architectures.
4. **Learning Loop:** Implemented feedback-driven procedural reinforcement where successful fixes increase runbook confidence.

### Verification & Testing Commands
```bash
.venv/bin/pytest tests/unit/test_eval_harness.py
cli eval --cases eval/cases.jsonl
cli consolidate
```

### Video & Presentation Speaking Part
- **Scene 4 & 5 (1:45 - 2:45):** Resolution to post-mortem workflow, runbook reinforcement, and presenting the Quantitative Benchmark & Ablation table.

---

## 🧑‍💻 Member 6: Interface & Developer Experience Lead

### Primary Role
**Slack Bolt Bot, REST API, Code Memory PR-Check & Submission Delivery**

### Code Ownership
- [app/slack/bot.py](../app/slack/bot.py): Slack Bolt Socket Mode bot with Block Kit cards, modals, and interactive buttons.
- [app/api/main.py](../app/api/main.py): FastAPI server with Alertmanager/PagerDuty webhooks, investigate, resolve, and `X-API-Key` auth.
- [app/code_memory/git_indexer.py](../app/code_memory/git_indexer.py): Git commit and function-level hunk indexing.
- [app/code_memory/pr_check.py](../app/code_memory/pr_check.py): Proactive PR risk scanner flagging files tied to historical outages.
- [docs/DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md) & [docs/SLIDES.md](SLIDES.md): Demo storyboard and pitch presentation.

### Key Responsibilities & Deliverables
1. **Slack Integration:** Full Socket Mode bot providing on-call engineers with in-thread analysis, helpful/unhelpful feedback buttons, and resolve modals.
2. **REST API:** Webhook receivers for Alertmanager and PagerDuty with background task processing.
3. **Proactive Prevention (`pr-check`):** Warns engineers before code merges when modified files caused past production outages.
4. **Submission Packaging:** Prepared video recording setup, pitch slides, and demo flow.

### Verification & Testing Commands
```bash
.venv/bin/pytest tests/unit/test_slack_bot.py tests/integration/test_healthz.py
cli pr-check --files services/checkout/OrderClient.py
```

### Video & Presentation Speaking Part
- **Scene 4 Co-presenter (1:45 - 2:15):** Demonstrating the proactive `pr-check` command warning a developer before deploying risky code.
- **Coordination:** Video recording, audio syncing, and Devpost submission checklist.

---

## 📋 Comprehensive Team Verification Matrix

| Area | Primary Owner | Secondary Owner | Acceptance Criteria | Passing Status |
| :--- | :---: | :---: | :--- | :---: |
| **System Scaffolding & Safety** | Member 1 | Member 4 | `ALLOW_ACTIONS=false`, zero mutating tools, type-hinted | ✅ Verified |
| **Working Memory & Redaction** | Member 2 | Member 6 | 0 secrets leaked, Redis 72h TTL, clean normalization | ✅ Verified |
| **Hippocampal Hybrid Retrieval** | Member 3 | Member 5 | p50 latency < 500ms (achieved 3.72ms), HNSW index | ✅ Verified |
| **Agent Reasoning & Scenarios** | Member 4 | Member 1 | Scenarios A, B, C, D passing, 0 hallucinated citations | ✅ Verified |
| **Ablation & Continuous Learning** | Member 5 | Member 3 | Hybrid Recall@3 beats baselines, sleep-replay patterns | ✅ Verified |
| **Slack Bot, REST API & PR-Check** | Member 6 | Member 2 | Socket mode operational, PR-check flags historical risks | ✅ Verified |

---

## 🚀 Pre-Submission Checklist (Run Before Pitch)

- [x] Run full test suite: `.venv/bin/pytest tests/` (36/36 passed in ~3s).
- [x] Run static analysis: `.venv/bin/ruff check .` (0 errors, 100% clean).
- [x] Run retrieval evaluation: `cli eval` (Generates [eval/report.md](../eval/report.md)).
- [x] Verify PR risk scanner: `cli pr-check --files services/checkout/OrderClient.py`.
- [x] Record 3-minute demo video following [docs/DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md).
- [x] Review pitch deck following [docs/SLIDES.md](SLIDES.md).
