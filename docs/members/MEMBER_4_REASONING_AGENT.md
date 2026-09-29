# 🧑‍💻 Member 4: Reasoning Agent & Tooling Developer

## 🎯 Role Overview
**Title:** Reasoning Agent & Tooling Developer  
**Core Domain:** Claude 3.5 Sonnet ReAct Reasoning Loop, 9 Read-Only Infrastructure Tools, Safety Dispatch Guards, Citation Integrity (Zero Hallucinations), and Outage Scenario Simulation.

---

## 📦 Code Ownership & Deliverables

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Reasoning Agent** | `app/agent/investigate.py` | ReAct reasoning loop, hypothesis formulation, evidence gathering, citation validation, confidence capping |
| **Tool Definitions** | `app/agent/tools.py` | 9 read-only tool schemas with strict dispatch guards |
| **Telemetry Adapters** | `app/adapters/base.py`, `app/adapters/mock.py` | Abstract interfaces and high-fidelity mock adapters for logs, metrics, deploys, and service topology |
| **LLM Orchestration** | `app/llm/client.py`, `app/llm/prompts.py` | Anthropic client with tenacity retry logic and structured XML prompts |
| **Outage Scenarios** | `data/mock_env/scenarios/` | Realistic failure scenarios: A (pool leak), B (cert expiry), C (novel error), D (look-alike DNS) |
| **Scenario Setup** | `scripts/create_mock_scenarios.py` | Setup script for mock incident data and telemetry |

---

## 🛡️ Key Architectural Guardrails
1. **Deterministic Confidence Rules**:
   - Caps confidence to `low` when strong mismatch flags exist.
   - Requires best precedent score $\ge 0.60$ AND live evidence from tool execution to award `high` confidence.
   - Complete novelty forces precedent strength to `none`.
2. **Citation Integrity (0 Hallucinations)**:
   - Automated post-processing checks every cited incident and runbook against memory.
   - Any hallucinated ID is immediately stripped into `dropped_citations` and confidence is penalized.
3. **Read-Only Safety Guarantee**:
   - Tools can only execute telemetry queries (`query_logs`, `query_metrics`, `get_recent_deploys`, etc.).
   - Remediations (rollbacks, restarts) are returned under `needs_human_decision`.

---

## 🧪 Verification & Acceptance Tests

```bash
# 1. Verify agent scenarios and confidence rules unit tests
PYTHONPATH="" .venv/bin/pytest tests/unit/test_agent_scenarios.py tests/unit/test_confidence_rules.py -v

# 2. Run live investigation on Scenario A (Connection Pool Exhaustion)
PYTHONPATH="" .venv/bin/python -m app.cli investigate --scenario A_pool_exhaustion

# 3. Run live investigation on Scenario C (Honest AI: Novel Error)
PYTHONPATH="" .venv/bin/python -m app.cli investigate --scenario C_novel
```

---

## 🎤 Presentation & Demo Role
- **Scene 2 (0:35 - 1:15):** Live terminal walkthrough of Scenario A: alert arrival, tool queries to logs/metrics, and evidence-cited analysis generation.
