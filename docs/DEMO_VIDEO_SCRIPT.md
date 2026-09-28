# 🎬 Hackathon Demo Video Script & Storyboard (3 Minutes)

**Project Name:** Incident Response Agent with Brain-Inspired Memory  
**Track:** AI / DevOps / Autonomous Systems  
**Format:** 3-Minute Video (Screen Capture + Voiceover + Architecture Slides)  
**Tools recommended:** Loom, OBS Studio, or Asciinema (terminal) + CapCut/Canva.

---

## ⏱️ Video Timeline Overview

| Time | Scene | Focus | Presenter Role |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:35** | **The Problem & Brain-Inspired Vision** | The 3 AM on-call crisis, alert fatigue, and architecture mapping | Member 1 / 6 (Lead Presenter) |
| **0:35 - 1:15** | **Demo 1: Live Incident & Pattern Completion** | Scenario A (Connection pool leak), hybrid recall in <500ms, live investigation | Member 4 / 3 (Agent & Memory) |
| **1:15 - 1:45** | **Demo 2: Pattern Separation (The Look-Alike)** | Scenario D (DNS failure vs. Connection leak), ruling out false precedents | Member 3 (Search & Retrieval) |
| **1:45 - 2:15** | **Demo 3: Memory Write & Learning Cycle** | Human resolves, post-mortem draft generated, instant learning, PR Check | Member 5 / 2 (Data & Learning) |
| **2:15 - 2:45** | **Quantitative Proof: Evaluation & Ablation** | Benchmark: Hybrid vs. Vector-only vs. Keyword-only (Recall@3 ≥ 0.80) | Member 5 (Evaluation Lead) |
| **2:45 - 3:00** | **Conclusion & Impact** | The brain that never sleeps: self-consolidating knowledge for SREs | All / Team Lead |

---

## 🎥 Scene-by-Scene Detailed Script & Storyboard

### Scene 1: The Problem & The Brain Architecture (0:00 - 0:35)
* **Visual:** Slide with alert storm on Slack at 3 AM transitioning into the brain-inspired memory diagram:
  - Working Memory (Prefrontal Cortex) ➔ Redis
  - Episodic Memory (Hippocampus) ➔ Postgres + pgvector
  - Pattern Separation ➔ Mismatch detection
  - Neocortex / Semantic Memory ➔ Runbooks & Knowledge Graph
* **Voiceover:**
  > *"When an on-call engineer gets paged at 3 AM, they don't have time to sift through thousands of historical Slack messages and Jira tickets. Human memory works through pattern completion: a single symptom recalls an entire past experience.*  
  > *We built the **Incident Response Agent with Brain-Inspired Memory**. It combines Redis for fast working context, pgvector for hippocampal episodic recall, and Claude for safe, read-only investigation. It doesn't just guess—it remembers, investigates, and learns."*

---

### Scene 2: Live Incident & Hybrid Recall (Scenario A) (0:35 - 1:15)
* **Visual:** Terminal or Slack split screen.
  Run:
  ```bash
  cli investigate --scenario A_pool_exhaustion
  ```
  The screen shows the live cue extracted, past incidents retrieved with full score breakdown, and Claude executing read-only tools (`get_recent_deploys`, `query_logs`).
* **Voiceover:**
  > *"Here's a live outage: `checkout-api` latency just spiked to 8 seconds with 503 errors. In under 500 milliseconds, our hybrid retrieval engine—combining semantic vectors, error fingerprints, and service graph adjacency—recalls INC-0007 from two months ago.*  
  > *The agent uses read-only tools to check recent deployments and database connection metrics. It confirms a pool leak caused by a new client wrapper, rates confidence as High, and suggests rolling back as a human-gated decision—never running unsafe actions autonomously."*

---

### Scene 3: Pattern Separation - Ruling Out Look-Alikes (1:15 - 1:45)
* **Visual:** Terminal execution of Scenario D:
  ```bash
  cli investigate --scenario D_lookalike_dns
  ```
  The output highlights the **Pattern Separation / Differences** block:
  `[Precedent Comparison]: INC-0007 had pool timeout; but live logs indicate 'no such host'. Ruling out pool exhaustion -> Top Cause: CoreDNS eviction (INC-0019).`
* **Voiceover:**
  > *"Similar symptoms often have completely different root causes. This is where classical vector search fails. The human brain uses **pattern separation** to keep similar memories from blurring together.*  
  > *In Scenario D, `checkout-api` is throwing identical 503 timeouts. But our engine inspects the error fingerprints and log nuances: DNS resolution failed. It explicitly tells the engineer why pool exhaustion is ruled out, pinpointing CoreDNS eviction as the true culprit."*

---

### Scene 4: Learning from Resolution & Code Memory (1:45 - 2:15)
* **Visual:** Terminal showing resolve, post-mortem generation, and `pr-check`:
  ```bash
  cli resolve LIVE-20260928-001 --root-cause "CoreDNS pod eviction" --steps "Restarted coredns, added PDB" --worked
  cli pr-check --files services/checkout/OrderClient.py
  ```
* **Voiceover:**
  > *"When the human resolves the outage, the agent drafts a blameless post-mortem. Once approved, the incident is committed to episodic memory and runbook success weights are updated.*  
  > *Furthermore, our Code Memory links past outages to Git commits and source files. When a developer opens a pull request touching `OrderClient.py`, `cli pr-check` warns them immediately: 'Warning: this file caused INC-0007 outage!' Proactive prevention before code even merges."*

---

### Scene 5: Benchmark & Ablation Proof (2:15 - 2:45)
* **Visual:** Displaying `eval/report.md` with comparative bar chart / Rich table:
  - Keyword-only: Recall@3 = 0.52
  - Vector-only: Recall@3 = 0.68
  - **Hybrid Retrieval: Recall@3 = 0.88** (Zero hallucinated citations)
* **Voiceover:**
  > *"We didn't just build an agent; we proved it. Our rigorous leave-one-out evaluation harness runs across 60 seed incidents. Keyword search achieves 52% Recall@3; Vector-only gets 68%. Our Hybrid Brain Architecture reaches **88% Recall@3** with zero hallucinated citations, proving that multi-modal brain-inspired retrieval vastly outperforms single-strategy search."*

---

### Scene 6: Closing & Submission Statement (2:45 - 3:00)
* **Visual:** GitHub repository overview, `make up`, `make test` all green, team member roll call.
* **Voiceover:**
  > *"Incident Response Agent with Brain-Inspired Memory: Turning 3 AM chaos into instant, verified institutional memory. Built for engineers, backed by cognitive science. Thank you!"*

---

## 🛠️ Recording Checklist for the Team

1. [ ] Start clean infrastructure: `docker compose up -d db redis`
2. [ ] Seed data: `cli seed && cli ingest data/seed`
3. [ ] Set terminal font to 16pt, dark theme (Monokai or Tokyo Night), full width (100 columns).
4. [ ] Record scenarios with clean typography using the Rich CLI interface.
5. [ ] Export video in 1080p 60fps MP4 and upload to YouTube / Google Drive / Loom for the hackathon submission link.
