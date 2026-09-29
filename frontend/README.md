# 🧠 Incident Brain: Enterprise Flutter UI & Command Center

High-fidelity cross-platform (Web, Linux, macOS, Windows) dashboard for the **Incident Response Agent with Brain-Inspired Memory** (Hack With Hyderabad 3.0 / Devnovate Hackathon).

---

## 🌟 Highlights & UI Score Multipliers

- **Modern Cyberpunk / SRE Glassmorphism Aesthetic:** Dark background (`#090D16`), glassmorphic panels, glowing neon status accents (Electric Cyan, Emerald, Amber, Rose, Indigo).
- **Sub-5ms Recall Visualizer:** Interactive 5-signal hippocampal fusion breakdown (Dense Vector 45%, BM25 20%, Stack Trace Fingerprint 20%, Topology 10%, Code 5%).
- **Interactive Slack Block Kit Card Simulator:** Live preview of what on-call engineers receive in Slack, including hypothesis evidence, recommended runbooks, human-in-the-loop action buttons, and reinforcement learning feedback voting (👍 / 👎).
- **Proactive PR Outage Risk Scanner:** Pre-merge gate scanning pull request diffs against historical post-mortems with risk score meters and warnings.
- **Sleep-Replay Consolidation Hub:** Visualizing agglomerative clusters and Laplace-smoothed empirical runbook success probabilities:
  $$p_{\text{runbook}} = \frac{S + 1}{S + F + 2}$$
- **Quantitative Ablation Matrix:** Side-by-side benchmark table comparing Hippocampal Hybrid Fusion against baselines (BM25 Only, Vector Only, No Fingerprint) showing 100.0% Recall@3 with 1.86ms p50 latency.
- **6-Member Architecture Map:** Visual breakdown of roles, deliverables, and live system health status (`/healthz` ping for PostgreSQL & Redis).

---

## 🚀 Running the Flutter App

### Prerequisites
- Flutter SDK 3.24+ (Web and Linux desktop enabled)
- Google Chrome or Linux desktop environment

### 1. Run in Chrome (Web)
```bash
cd frontend
flutter run -d chrome
```

### 2. Run on Linux Desktop
```bash
cd frontend
flutter run -d linux
```

### 3. Build Web Release (Served by FastAPI)
```bash
cd frontend
flutter build web --release
```
Once built, starting the backend:
```bash
uv run uvicorn app.api.main:app --port 8000 --reload
```
will automatically mount and serve the Flutter application at:
- **`http://localhost:8000/app/`**
- **`http://localhost:8000/`** (redirects to Flutter app when built, or serves unified HTML portal)
- **`http://localhost:8000/portal`** (unified HTML fallback portal)
