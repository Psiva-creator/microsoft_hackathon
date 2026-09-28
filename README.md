# 🧠 Incident Response Agent with Brain-Inspired Memory

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Tests: 36 Passed](https://img.shields.io/badge/tests-36%20passed-brightgreen.svg)](tests/)
[![Ruff Clean](https://img.shields.io/badge/code%20style-ruff%20100%25-000000.svg)](https://github.com/astral-sh/ruff)
[![PostgreSQL 16](https://img.shields.io/badge/postgres-16%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Redis 7](https://img.shields.io/badge/redis-7%20AOF-DC382D.svg)](https://redis.io/)
[![Claude 3.5 Sonnet](https://img.shields.io/badge/LLM-Claude%203.5%20Sonnet-6B4FBB.svg)](https://www.anthropic.com/)

> **Submission for Hack With Hyderabad 3.0 / Devnovate Hackathon**  
> An autonomous on-call assistant that models the human brain's memory systems to recall past incidents, safely investigate live outages using read-only tools, rule out deceptive look-alikes via pattern separation, and continuously learn from resolved post-mortems and engineer feedback.

---

## 📑 Quick Navigation
- [🎯 The Vision & Biological Inspiration](#-the-vision--biological-inspiration)
- [🏗️ System Architecture](#️-system-architecture)
- [⚡ 5-Command Quickstart](#-5-command-quickstart)
- [🎬 Demo Scenarios Walkthrough](#-demo-scenarios-walkthrough)
- [📊 Quantitative Benchmark & Ablation](#-quantitative-benchmark--ablation)
- [🛡️ Enterprise Safety & Guardrails](#️-enterprise-safety--guardrails)
- [💻 Proactive Code Memory (`pr-check`)](#-proactive-code-memory-pr-check)
- [💬 Slack Bot (Socket Mode) & REST API](#-slack-bot-socket-mode--rest-api)
- [👥 6-Member Team Delegation](#-6-member-team-delegation)
- [🎥 Video Script, Slides & Architecture Decisions](#-video-script-slides--architecture-decisions)

---

## 🎯 The Vision & Biological Inspiration

When production breaks at 3 AM, on-call engineers are inundated with alert storms, cryptic logs, and fragmented telemetry. Crucial institutional knowledge—previous outages, fixes that worked, and runbooks that failed—is buried across thousands of old Slack threads and closed Jira tickets.

Human memory solves this through **pattern completion**: a partial cue (e.g. `HikariPool connection timeout`) immediately brings back the entire past experience.

We modeled the **Incident Response Agent** on the human brain's memory systems:

| Brain Region | Biological Role | Our Implementation |
| :--- | :--- | :--- |
| **Working Memory (Prefrontal Cortex)** | Holds what is happening right now | **Redis 7**: Live incident context, events timeline, active hypotheses (72h TTL) |
| **Hippocampus (Episodic Memory)** | Stores whole events; a partial cue brings back the full episode | **PostgreSQL 16 + pgvector**: Multi-modal hybrid recall in **<4ms** |
| **Pattern Separation** | Prevents similar memories from blurring together | **Deterministic Mismatch Flags**: Distinguishes look-alikes (e.g. DNS vs. pool exhaustion) |
| **Neocortex (Semantic Memory)** | General facts, service topologies, and rules | **Dependency Graph & Runbook Store**: Services, runbooks, and patterns |
| **Procedural Memory** | Learned skills and muscle memory | **Success-Weighted Runbooks**: Laplace-smoothed probability scores updated by feedback |
| **Consolidation (Sleep Replay)** | Turns episodes into generalized patterns | **Nightly Clustering Job**: Agglomerative clustering and half-life decay of stale architectures |
| **Working to Long-Term Transfer** | Experiences become lasting memories | **Post-Mortem Writeback**: Human-approved post-mortem committed with dual embeddings |

---

## 🏗️ System Architecture

```
                 Alert / Webhook / Slack / CLI
                              │
                              ▼
┌──────────────────────────────────────────────────────────┐
│             REDACTION & NORMALIZATION ENGINE             │
│   Scrubs AWS, GitHub, Slack tokens, JWTs, passwords, PII  │
└─────────────────────────────┬────────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
┌──────────────────────────────┐ ┌─────────────────────────────────────────┐
│     REDIS WORKING MEMORY     │ │      REASONING AGENT (Claude 3.5)       │
│  (Live context, events, TTL) │ │ 1. Build Cue ➔ 2. Recall ➔ 3. Investigate│
└──────────────┬───────────────┘ └──────┬────────────────────┬─────────────┘
               │                        │ recall(cue)        │ read-only tools
               │                        ▼                    ▼
               │         ┌─────────────────────────┐ ┌─────────────────────┐
               │         │ RETRIEVAL ENGINE (<4ms) │ │ READ-ONLY ADAPTERS  │
               │         │ Vector + Full-Text +    │ │ Logs, Metrics,      │
               │         │ Fingerprint + Graph     │ │ Deploys, Git history│
               │         └──────────────┬──────────┘ └─────────────────────┘
               │                        ▼
               │         ┌─────────────────────────────────────────────────┐
               │         │       POSTGRESQL 16 + PGVECTOR LONG-TERM STORE  │
               │         │ Incidents · Runbooks · Patterns · Code Links    │
               │         └──────────────▲────────────────────▲─────────────┘
               │                        │                    │
               │         ┌──────────────┴──────────┐  ┌──────┴─────────────┐
               └────────▶│ POST-MORTEM & WRITEBACK │  │ CONSOLIDATION JOB  │
                         │ Resolve ➔ Human Approval│  │  (Sleep Replay)    │
                         └─────────────────────────┘  └────────────────────┘
```

---

## ⚡ 5-Command Quickstart

Get the entire system running in under 2 minutes:

```bash
# 1. Install dependencies into virtual environment
make install

# 2. Run the complete test suite (36 tests, 100% pass)
make test

# 3. Seed episodic memory with 64 incidents, services, and 8 runbooks
make seed

# 4. Run the quantitative retrieval benchmark & ablation suite
make eval

# 5. Run full agent investigation on a live outage scenario
.venv/bin/python -m app.cli investigate --scenario A_pool_exhaustion
```

---

## 🎬 Demo Scenarios Walkthrough

The platform ships with 4 end-to-end incident scenarios in [`data/mock_env/scenarios/`](data/mock_env/scenarios/):

### 1. Scenario A: Connection Pool Exhaustion (`A_pool_exhaustion`)
- **Trigger:** `checkout-api` latency spikes to 8s with HTTP 503 errors after deploy `v212`.
- **Hippocampal Recall:** Recalls `INC-0007` from 2 months ago in **3.72 ms** ($sim = 0.91$).
- **Investigation:** Claude calls read-only tools (`get_recent_deploys`, `query_logs`, `query_metrics`) to confirm HikariPool saturation caused by unclosed connections in `OrderClient.py`.
- **Safety Action:** Surfaces rollback recommendation under `needs_human_decision` (never mutates infrastructure autonomously).

```bash
.venv/bin/python -m app.cli investigate --scenario A_pool_exhaustion
```

### 2. Scenario D: Pattern Separation & Look-Alikes (`D_lookalike_dns`)
- **The Challenge:** `checkout-api` is throwing identical 503 timeouts as Scenario A. Classical vector search fails by retrieving `INC-0007` and guessing pool exhaustion.
- **Brain-Inspired Separation:** Our engine inspects stack trace fingerprints and log nuances (`dial tcp: lookup postgres-primary: no such host`).
- **Precedent Comparison:** Explicitly flags `trigger_mismatch`, rules out pool exhaustion, and pinpoints `INC-0019` (CoreDNS pod eviction) as the true culprit.

```bash
.venv/bin/python -m app.cli investigate --scenario D_lookalike_dns
```

### 3. Scenario B: Expired TLS Certificate (`B_cert_expiry`)
- **Trigger:** `payments-gateway` webhook handshake failures.
- **Recall & Verification:** Recalls `INC-0012` and inspects certificates. Recommends running `RB-cert-expiry`.

```bash
.venv/bin/python -m app.cli investigate --scenario B_cert_expiry
```

### 4. Scenario C: Novel Outage (`C_novel_error`)
- **The Challenge:** Outage with zero historical precedent in episodic memory.
- **Honest AI Guardrail:** Rather than hallucinating or forcing a false precedent, the agent explicitly outputs `precedent_strength: "none"` and caps confidence to `low`.

```bash
.venv/bin/python -m app.cli investigate --scenario C_novel_error
```

---

## 📊 Quantitative Benchmark & Ablation

We evaluated the Hippocampal Retrieval Engine across **60 leave-one-out benchmark cases** (excluding the source incident ID so the engine must retrieve a related precedent):

```bash
.venv/bin/python -m app.cli eval --cases eval/cases.jsonl
```

### Results Summary ([eval/report.md](eval/report.md)):

| Retrieval Mode | Recall@1 | Recall@3 | Recall@5 | MRR | p50 Latency | Target Met |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Keyword (FTS only)** | 60.0% | 78.3% | 86.7% | 0.706 | 1.89 ms | Baseline |
| **Vector (BGE Embeddings only)** | 46.7% | 61.7% | 75.0% | 0.568 | 3.42 ms | Baseline |
| **Hybrid (Full Brain Architecture)** | **61.7%** | **78.3%** | **86.7%** | **0.706** | **3.72 ms** | ✅ **PASS** |
| *Ablation: without Vector* | 48.3% | 63.3% | 76.7% | 0.584 | 1.76 ms | Drop |
| *Ablation: without FTS* | 45.0% | 58.3% | 70.0% | 0.535 | 3.36 ms | Drop |
| *Ablation: without Fingerprints* | 46.7% | 60.0% | 68.3% | 0.543 | 3.89 ms | Major Drop |

### Key Takeaways:
1. **Speed SLA:** Achieved **3.72 ms retrieval time**—over 100x faster than the 500ms target.
2. **Zero Hallucinated Citations:** 100% of cited incident IDs are verified in database.
3. **Pattern Separation:** Removing stack trace fingerprints causes a steep drop in accuracy, proving error fingerprints are critical for separating look-alikes.

---

## 🛡️ Enterprise Safety & Guardrails

1. **The Read-Only Rule:** The agent tool registry is strictly read-only (`ALLOW_ACTIONS=false`). Remediations (rollbacks, restarts, config changes) are surfaced under `needs_human_decision` for human sign-off.
2. **Deterministic Confidence Guardrails:**
   - Confidence is automatically capped at `low` when strong mismatch flags are present.
   - When no precedent exists (Scenario C), confidence is forced to `low`.
   - Any hallucinated citation is stripped into `dropped_citations` and penalizes confidence.
3. **Zero-Leak Redaction Engine ([app/core/redact.py](app/core/redact.py)):**
   - Automatically sanitizes AWS access keys, GitHub tokens, Slack tokens, JWTs, Bearer credentials, and private keys before text touches any model or persistent storage.

---

## 💻 Proactive Code Memory (`pr-check`)

When an engineer opens a pull request, the agent proactively warns if the modified code caused outages in the past:

```bash
.venv/bin/python -m app.cli pr-check --files services/checkout/OrderClient.py
```

```text
PR Risk Assessment: HIGH
Past Outages Linked to Modified Code:
┌─────────────┬────────────────────────────────────┬────────────┬──────────────────────────────────────┐
│ Incident ID │ File Path                          │ Role       │ Historical Root Cause                │
├─────────────┼────────────────────────────────────┼────────────┼──────────────────────────────────────┤
│ INC-0007    │ services/checkout/OrderClient.py   │ root_cause │ Database connection pool exhaustion  │
└─────────────┴────────────────────────────────────┴────────────┴──────────────────────────────────────┘

🛡️ Proactive Safety Recommendations:
  • Verify database connection release in exception blocks (try-with-resources).
  • Check staging connection pool metrics prior to deploying to production.
```

---

## 💬 Slack Bot (Socket Mode) & REST API

### Slack Bot ([app/slack/bot.py](app/slack/bot.py))
- Runs in **Socket Mode** using `slack-bolt` (no public webhook URL required).
- Mention `@IncidentBot <problem>` or use `/incident start <title>`.
- Posts structured Block Kit cards in a dedicated incident thread.
- Interactive buttons: **Helpful**, **Not helpful**, **Investigate again**, and **Mark resolved**.
- **Mark resolved** opens a modal to submit root cause, steps, and runbooks used, drafting a post-mortem for one-click approval into memory.

### REST API ([app/api/main.py](app/api/main.py))
- `GET /healthz`: PostgreSQL and Redis health connectivity.
- `POST /webhooks/alertmanager`: Prometheus Alertmanager webhook triggering automated investigation.
- `POST /webhooks/pagerduty`: PagerDuty v3 incident webhook.
- `POST /incidents/{id}/investigate`: On-demand investigation.
- `POST /incidents/{id}/resolve`: Incident resolution & post-mortem generation.
- `POST /pr-check`: CI/CD PR check endpoint.

---

## 👥 6-Member Team Delegation & Complete Work Details

For full individual dossiers, see [docs/TEAM_SPLIT.md](docs/TEAM_SPLIT.md). Below is the comprehensive work distribution across the 6 team members:

### 🧑‍💻 Member 1: Team Lead & Systems Architect ([Dossier](docs/members/MEMBER_1_SYSTEMS_ARCHITECT.md) · [Branch](https://github.com/ved354/microsoft_hackathon/tree/member-1-systems-architect))
- **Domain & Scaffolding:** Configured centralized `app/config.py` using `pydantic-settings`, structured JSON/console logging with `structlog`, and unified Pydantic v2 domain schemas (`Cue`, `Analysis`, `Hypothesis`, `LiveContext`).
- **Core Guardrails:** Enforced strict read-only safety policy (`ALLOW_ACTIONS=false`) across all tool definitions and dispatcher.
- **Terminal Orchestrator:** Developed the rich terminal CLI (`cli.py`) with colored confidence badges, evidence tables, and runbook links.
- **Scaffolding & CI:** Configured `pyproject.toml`, `docker-compose.yml`, `Dockerfile`, and `Makefile`.
- **Verification Commands:**
  ```bash
  .venv/bin/pytest tests/unit/test_scaffold.py tests/unit/test_tools_readonly.py
  .venv/bin/ruff check .
  .venv/bin/python -m app.cli --help
  ```

### 🧑‍💻 Member 2: Working Memory & Ingestion Engineer ([Dossier](docs/members/MEMBER_2_WORKING_MEMORY.md) · [Branch](https://github.com/ved354/microsoft_hackathon/tree/member-2-working-memory-ingestion))
- **Prefrontal Cortex (Redis):** Implemented `app/memory/working.py` storing live incident timeline, incoming events, active hypotheses, and automatic 72-hour TTL expiration upon resolution.
- **Zero-Leak Redaction:** Built `app/core/redact.py` scrubbing AWS keys, GitHub tokens, Slack tokens, JWTs, Bearer headers, private keys, and passwords.
- **Normalization:** Created `app/core/normalize.py` abstracting timestamps, UUIDs, IP addresses, and numbers while safely preserving HTTP status codes (`HTTP/1.1 502`).
- **Data Ingestion Pipeline:** Created `app/ingestion/loaders.py` and `app/ingestion/pipeline.py` processing 64 diverse incident documents (markdown post-mortems, Jira JSON, Slack transcripts) with SHA-256 deduplication and near-duplicate cosine matching ($\ge 0.97$).
- **Verification Commands:**
  ```bash
  .venv/bin/pytest tests/unit/test_redact.py tests/unit/test_normalize.py
  .venv/bin/python -m app.cli seed
  ```

### 🧑‍💻 Member 3: Hippocampal Search & Retrieval Specialist ([Dossier](docs/members/MEMBER_3_HIPPOCAMPAL_RETRIEVAL.md) · [Branch](https://github.com/ved354/microsoft_hackathon/tree/member-3-hippocampal-retrieval))
- **Dual Representation Embeddings:** Developed `app/core/embeddings.py` using local `BAAI/bge-small-en-v1.5` (384 dimensions) with persistent SQLite caching. Symptoms and full post-mortems are indexed separately to prevent cue bias.
- **Stack Trace Fingerprinting:** Built `app/core/fingerprint.py` parsing multi-language stack traces (Python, Java, Node.js, Go) to extract innermost application frames and compute SHA-1 fingerprints.
- **Hippocampal Retrieval Engine:** Implemented `app/memory/retrieval.py` unifying Vector ($W=0.45$), FTS ($W=0.20$), Fingerprints ($W=0.20$), Service Graph ($W=0.10$), and Code History ($W=0.05$). Achieved **3.72 ms** p50 retrieval latency.
- **Pattern Separation:** Created deterministic mismatch flags (`trigger_mismatch`, `service_mismatch`, `fix_did_not_work`, `old`) to rule out false look-alikes.
- **Verification Commands:**
  ```bash
  .venv/bin/pytest tests/unit/test_embeddings.py tests/unit/test_fingerprint.py
  .venv/bin/python -m app.cli ask "checkout-api 503s and p99 8s after deploy" --service checkout-api
  ```

### 🧑‍💻 Member 4: Reasoning Agent & Tooling Developer ([Dossier](docs/members/MEMBER_4_REASONING_AGENT.md) · [Branch](https://github.com/ved354/microsoft_hackathon/tree/member-4-reasoning-agent))
- **Claude ReAct Loop:** Built `app/agent/investigate.py` managing hypothesis formulation, tool calling, evidence accumulation, and confidence capping.
- **Read-Only Telemetry Adapters:** Implemented `app/agent/tools.py`, `app/adapters/base.py`, and `app/adapters/mock.py` providing safe queries to logs, metrics, deploys, and service topology without mutating real infrastructure.
- **Deterministic Confidence Rules:** Capped confidence to `low` when strong mismatch flags exist, `none` precedent forces `low`, and zero citations trigger auto-downgrades.
- **Citation Integrity:** Built automated citation verification guaranteeing 0 hallucinated citations (all cited IDs must exist in memory; invalid IDs are placed in `dropped_citations`).
- **Verification Commands:**
  ```bash
  .venv/bin/pytest tests/unit/test_agent_scenarios.py tests/unit/test_confidence_rules.py
  .venv/bin/python -m app.cli investigate --scenario A_pool_exhaustion
  .venv/bin/python -m app.cli investigate --scenario C_novel_error
  ```

### 🧑‍💻 Member 5: Evaluation & Continuous Learning Lead ([Dossier](docs/members/MEMBER_5_EVAL_CONSOLIDATION.md) · [Branch](https://github.com/ved354/microsoft_hackathon/tree/member-5-eval-continuous-learning))
- **Evaluation Harness & Ablation:** Developed `app/eval/harness.py` running leave-one-out benchmarks across 60 evaluation cases (`eval/cases.jsonl`), generating `eval/report.md` and `eval/report.json`.
- **Sleep-Replay Consolidation:** Built `app/jobs/consolidate.py` using `AgglomerativeClustering` to cluster similar incidents into general `patterns`, synthesize preventive rules, and apply half-life decay to stale architectures.
- **Post-Mortem & Memory Writeback:** Built `app/agent/postmortem.py` generating blameless post-mortem drafts upon resolution and writing approved records back into long-term memory.
- **Procedural Memory Statistics:** Implemented `app/memory/stats.py` calculating Laplace-smoothed runbook success probabilities ($p = \frac{s + 1}{s + f + 2}$) reinforced by engineer feedback.
- **Verification Commands:**
  ```bash
  .venv/bin/pytest tests/unit/test_eval_harness.py
  .venv/bin/python -m app.cli eval --cases eval/cases.jsonl
  .venv/bin/python -m app.cli consolidate
  ```

### 🧑‍💻 Member 6: Interface & Developer Experience Lead ([Dossier](docs/members/MEMBER_6_INTERFACES_DEVREL.md) · [Branch](https://github.com/ved354/microsoft_hackathon/tree/member-6-interface-slack-api))
- **Slack Bolt Bot:** Built `app/slack/bot.py` in Socket Mode featuring rich Block Kit cards, thread discussions, `/reinvestigate`, interactive buttons (`Helpful`, `Not helpful`), and interactive resolve modal.
- **REST API:** Implemented `app/api/main.py` with `/healthz`, Prometheus Alertmanager webhooks, PagerDuty webhooks, investigate, and resolve endpoints.
- **Proactive Code Memory:** Developed `app/code_memory/git_indexer.py` and `app/code_memory/pr_check.py` linking git commits to past outages and warning developers before merging risky code.
- **Submission Packaging:** Produced the 3-minute demo script (`docs/DEMO_VIDEO_SCRIPT.md`) and pitch deck (`docs/SLIDES.md`).
- **Verification Commands:**
  ```bash
  .venv/bin/pytest tests/unit/test_slack_bot.py tests/integration/test_healthz.py
  .venv/bin/python -m app.cli pr-check --files services/checkout/OrderClient.py
  ```

---

## 🎬 3-Minute Demo Video Script & Storyboard

Full script with presenter notes is available in [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md):

| Timestamp | Scene | Screen Focus | Narration Key Points |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:35** | **The Crisis & Vision** | PagerDuty 3 AM alert storm ➔ Brain Memory Diagram | *"When an on-call engineer gets paged at 3 AM, they don't have time to sift through thousands of historical Slack messages. Human memory works through pattern completion. We built the Incident Response Agent with Brain-Inspired Memory."* |
| **0:35 - 1:15** | **Live Recall & Investigation** | `cli investigate --scenario A_pool_exhaustion` | *"checkout-api latency just spiked to 8 seconds. In under 4 milliseconds, our hybrid retrieval recalls INC-0007. Claude executes read-only tools to check logs and connection metrics, confirms a pool leak, and surfaces rollback as a human-gated decision."* |
| **1:15 - 1:45** | **Pattern Separation** | `cli investigate --scenario D_lookalike_dns` | *"Similar symptoms often have completely different root causes. In Scenario D, checkout-api throws identical 503s. But our engine inspects the stack traces: host lookup failure. It explicitly rules out pool exhaustion and pinpoints CoreDNS eviction (INC-0019)."* |
| **1:45 - 2:15** | **Learning & Code Memory** | `cli resolve` ➔ `cli pr-check` | *"When resolved, the agent drafts a blameless post-mortem. Once approved, the incident is committed to episodic memory. And our Code Memory links outages to Git commits: when a PR touches OrderClient.py, pr-check warns the developer immediately!"* |
| **2:15 - 2:45** | **Quantitative Proof** | Evaluation Table (`eval/report.md`) | *"We proved it across 60 leave-one-out incidents: Keyword gets 60% Recall@1; Vector gets 46.7%. Our Hybrid Brain reaches 61.7% Recall@1, 78.3% Recall@3, and 86.7% Recall@5 in 3.72ms with 0 hallucinated citations."* |
| **2:45 - 3:00** | **Conclusion** | Clean terminal with 36/36 green tests | *"Incident Response Agent: Turning 3 AM chaos into instant, verified institutional memory. Built for engineers, backed by cognitive science. Thank you!"* |

---

## 📑 12-Slide Pitch Deck Overview

Full slide contents and talking points are detailed in [docs/SLIDES.md](docs/SLIDES.md):

1. **Slide 1: Title & Hook** — Turning 3 AM On-Call Chaos into Instant Institutional Memory.
2. **Slide 2: The On-Call Crisis** — Alert storms, lost institutional knowledge, and deceptive look-alikes.
3. **Slide 3: Biological Inspiration** — Cognitive mapping table (Prefrontal Cortex, Hippocampus, Neocortex, Procedural).
4. **Slide 4: System Architecture** — End-to-end data flow from alert to long-term memory writeback.
5. **Slide 5: Live Demo 1 (Scenario A)** — Sub-4ms recall and read-only telemetry investigation.
6. **Slide 6: Live Demo 2 (Scenario D)** — Pattern separation ruling out deceptive look-alikes (DNS vs pool leak).
7. **Slide 7: Continuous Learning Loop** — Resolve ➔ Post-mortem draft ➔ Human approval ➔ Long-term memory write.
8. **Slide 8: Proactive Prevention** — Git code memory and `pr-check` in CI/CD.
9. **Slide 9: Enterprise Safety & Guardrails** — Strict read-only tools, zero hallucinations, secret redaction.
10. **Slide 10: Quantitative Proof** — Benchmark and ablation results across 60 leave-one-out cases.
11. **Slide 11: Production-Grade Engineering** — 36/36 tests passing in 3.2s, 100% Ruff clean, containerized.
12. **Slide 12: Team & Future Roadmap** — Roll call of all 6 members and vision for enterprise SRE.

---

## 🏗️ 11-Phase Technical Implementation Summary

| Phase | Milestone | Core Components | Acceptance Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Core Scaffolding & Utilities** | Pydantic v2 schemas, secret redaction, normalization, stack trace fingerprinting, local BGE embeddings | ✅ Verified |
| **Phase 2** | **Long-Term Memory Store** | PostgreSQL 16 + pgvector schema, plain psycopg v3 pool, Laplace runbook success statistics | ✅ Verified |
| **Phase 3** | **Ingestion & Seed Data** | 64 synthetic incidents (post-mortems, Jira JSON, Slack logs), SHA-256 dedupe, near-duplicate check | ✅ Verified |
| **Phase 4** | **Read-Only Telemetry Adapters** | 9 read-only tool schemas, mock telemetry adapters for Scenarios A-D, safety dispatcher | ✅ Verified |
| **Phase 5** | **Reasoning Agent & CLI** | Claude ReAct loop, citation validation, deterministic confidence capping, Rich terminal UI | ✅ Verified |
| **Phase 6** | **Slack Bot Integration** | Socket Mode Bolt app, Block Kit cards, thread timeline, interactive feedback, resolve modal | ✅ Verified |
| **Phase 7** | **Resolution & Memory Writeback** | Resolution capture, post-mortem generation, human approval flow, 72h TTL close | ✅ Verified |
| **Phase 8** | **Code Memory & PR Check** | Git commit indexer, function hunk parsing, proactive PR risk scanner (`cli pr-check`) | ✅ Verified |
| **Phase 9** | **Sleep-Replay Consolidation** | Nightly Agglomerative Clustering into patterns, preventive rule synthesis, half-life decay | ✅ Verified |
| **Phase 10** | **Evaluation & Ablation Suite** | 60 leave-one-out benchmark cases, Keyword vs Vector vs Hybrid evaluation, latency profiling | ✅ Verified |
| **Phase 11** | **Hardening & Documentation** | Zero mutating tools, zero secret leaks, 100% ruff linting, 36/36 pytest pass | ✅ Verified |

---

## 🛠️ Complete Verification & Quality Commands

```bash
# 1. Run all unit and integration tests (36 tests pass in ~3.2 seconds)
.venv/bin/pytest tests/ -v

# 2. Check static analysis and type formatting (0 errors, 100% clean)
.venv/bin/ruff check .

# 3. Run the quantitative retrieval benchmark and ablation suite
.venv/bin/python -m app.cli eval --cases eval/cases.jsonl

# 4. Run live investigation on Scenario A (Connection pool exhaustion)
.venv/bin/python -m app.cli investigate --scenario A_pool_exhaustion

# 5. Run live investigation on Scenario D (Pattern separation / look-alike DNS)
.venv/bin/python -m app.cli investigate --scenario D_lookalike_dns

# 6. Run live investigation on Scenario C (Honest AI: precedent=none)
.venv/bin/python -m app.cli investigate --scenario C_novel_error

# 7. Run proactive PR risk scanner on code history
.venv/bin/python -m app.cli pr-check --files services/checkout/OrderClient.py

# 8. Check memory health statistics and runbook success rates
.venv/bin/python -m app.cli stats
```

---

## 🎥 Video Script, Slides & Architecture Decisions

- 🎬 **Demo Video Script & Storyboard (3 Minutes):** [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md)
- 📑 **Pitch Deck Outline (12 Slides):** [docs/SLIDES.md](docs/SLIDES.md)
- 👥 **Team Work Breakdown (6 Members):** [docs/TEAM_SPLIT.md](docs/TEAM_SPLIT.md)
- 📖 **Architectural Decision Records (ADRs):** [docs/DECISIONS.md](docs/DECISIONS.md)
- 📊 **Evaluation & Ablation Report:** [eval/report.md](eval/report.md)
- 📋 **Full Technical Specification:** [SPEC.md](SPEC.md)

---

*Built with ❤️ for on-call engineers by the Hack With Hyderabad 3.0 Team.*

