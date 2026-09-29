# 🧑‍💻 Member 1: Systems Architect & Core Guardrails

## 🎯 Role Overview
**Title:** Team Lead & Systems Architect  
**Core Domain:** System Orchestration, Pydantic Domain Schemas, Structured Logging, Configuration Management, Deterministic Safety Guardrails, and CLI Orchestration.

---

## 📦 Code Ownership & Deliverables

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Domain Models** | `app/models.py` | Canonical Pydantic v2 schemas: `Cue`, `Analysis`, `Hypothesis`, `ScoredIncident`, `LiveContext` |
| **Configuration** | `app/config.py` | Centralized environment settings (`pydantic-settings`), type-safe configs |
| **Structured Logging** | `app/logging.py` | Production-grade structured JSON and console logging (`structlog`) |
| **Unified CLI** | `app/cli.py` | Rich interactive terminal interface (`seed`, `ingest`, `ask`, `investigate`, `resolve`, `pr-check`, `consolidate`, `stats`, `eval`) |
| **Architecture Records** | `docs/DECISIONS.md` | Architectural Decision Records (ADRs) |
| **Project Scaffolding** | `pyproject.toml`, `docker-compose.yml`, `Dockerfile`, `Makefile`, `.env.example`, `.gitignore` | Packaging, containerization, and build scripts |

---

## 🛡️ Key Architectural Guardrails
1. **Zero Mutating Actions (`ALLOW_ACTIONS=false`)**:
   - The agent is strictly constrained to read-only actions (`query_logs`, `query_metrics`, `get_recent_deploys`, `get_service_dependencies`, `find_code_history`).
   - Any remediation actions (e.g. rollbacks, restarts) are strictly routed to `needs_human_decision` requiring explicit human approval.
2. **Unified Pydantic v2 Contracts**:
   - Ensures zero schema drift between FastAPI endpoints, CLI commands, Slack cards, and background jobs.
3. **Structured Contextual Logging**:
   - Structured key-value logging with correlation IDs for every incident investigation.

---

## 🧪 Verification & Acceptance Tests

```bash
# 1. Verify system scaffolding and read-only guardrails
PYTHONPATH="" .venv/bin/pytest tests/unit/test_scaffold.py tests/unit/test_tools_readonly.py -v

# 2. Verify static analysis and code hygiene
.venv/bin/ruff check .

# 3. Verify CLI help and memory health stats
PYTHONPATH="" .venv/bin/python -m app.cli --help
PYTHONPATH="" .venv/bin/python -m app.cli stats
```

---

## 🎤 Presentation & Demo Role
- **Scene 1 (0:00 - 0:35):** The 3 AM On-Call Crisis, alert fatigue, and the Brain-Inspired Memory vision.
- **Scene 6 (2:45 - 3:00):** Closing statement, enterprise safety guarantees, and wrap-up.
