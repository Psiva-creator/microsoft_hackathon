# 🧑‍💻 Member 5: Evaluation & Continuous Learning Lead

## 🎯 Role Overview
**Title:** Evaluation & Continuous Learning Lead  
**Core Domain:** Quantitative Evaluation Harness (Recall@k, MRR, Latency), Ablation Benchmarking across 60 Leave-One-Out Cases, Sleep-Replay Consolidation (Agglomerative Clustering), Post-Mortem Writeback Engine, and Laplace Runbook Reinforcement.

---

## 📦 Code Ownership & Deliverables

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Evaluation Harness** | `app/eval/harness.py` | Multi-mode leave-one-out evaluation suite benchmarking Keyword vs. Vector vs. Hybrid retrieval |
| **Benchmark Cases** | `eval/cases.jsonl` | 60 realistic leave-one-out test cases spanning diverse failure modes |
| **Benchmark Report** | `eval/report.md`, `eval/report.json` | Quantitative ablation report proving Hybrid superiority |
| **Sleep-Replay Consolidation** | `app/jobs/consolidate.py` | Agglomerative clustering ($\text{threshold}=0.35$), preventive rule generation, half-life decay |
| **Post-Mortem Engine** | `app/agent/postmortem.py` | Resolution capture, post-mortem generation, and long-term memory writeback |
| **Procedural Stats** | `app/memory/stats.py` | Laplace-smoothed runbook success probabilities ($p = \frac{s + 1}{s + f + 2}$) |
| **Incident Runbooks** | `data/runbooks/` | 8 operational markdown runbooks linked to incident classes |

---

## 📊 Quantitative Benchmark & Ablation Highlights
Across the 60 leave-one-out evaluation cases:
- **Hybrid Retrieval (Our System):** Recall@1: **0.867**, Recall@3: **0.950**, Recall@5: **0.983**, MRR: **0.914**, p50 Latency: **3.72ms**.
- **Vector-Only Baseline:** Recall@3: **0.783** (-16.7% vs Hybrid).
- **Keyword-Only Baseline:** Recall@3: **0.617** (-33.3% vs Hybrid).

---

## 🛡️ Continuous Learning Loop
1. **Sleep-Replay Consolidation:**
   - Clusters related historical incidents into generalized high-level `patterns`.
   - Synthesizes preventive rules with mandatory `exceptions_text`.
   - Decays stale weights of obsolete system architectures.
2. **Procedural Memory Reinforcement:**
   - Successful engineer resolutions boost runbook confidence via Bayesian Laplace smoothing.

---

## 🧪 Verification & Acceptance Tests

```bash
# 1. Verify evaluation harness unit tests
PYTHONPATH="" .venv/bin/pytest tests/unit/test_eval_harness.py -v

# 2. Run the quantitative retrieval evaluation benchmark
PYTHONPATH="" .venv/bin/python -m app.cli eval --cases eval/cases.jsonl

# 3. Trigger sleep-replay memory consolidation
PYTHONPATH="" .venv/bin/python -m app.cli consolidate
```

---

## 🎤 Presentation & Demo Role
- **Scene 4 & 5 (1:45 - 2:45):** Resolution to post-mortem workflow, runbook reinforcement, and presenting the Quantitative Benchmark & Ablation table.
