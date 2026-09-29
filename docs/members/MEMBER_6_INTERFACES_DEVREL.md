# 🧑‍💻 Member 6: Interface & Developer Experience Lead

## 🎯 Role Overview
**Title:** Interface & Developer Experience Lead  
**Core Domain:** Slack Bolt Socket Mode Bot (Interactive UI), FastAPI REST API with Webhooks, Proactive Git Code Memory & PR Risk Scanner (`cli pr-check`), Video Storyboard, Pitch Slides, and Submission Delivery.

---

## 📦 Code Ownership & Deliverables

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Slack Bolt Bot** | `app/slack/bot.py` | Full Socket Mode bot with Block Kit cards, investigation timelines, interactive helpful/unhelpful buttons, and resolution modal |
| **FastAPI REST Server**| `app/api/main.py` | REST API with Alertmanager and PagerDuty webhook receivers, `X-API-Key` auth, and health endpoints |
| **Git Code Indexer** | `app/code_memory/git_indexer.py` | Git commit history indexer parsing function-level diff hunks |
| **Proactive PR Check** | `app/code_memory/pr_check.py` | CI/CD PR risk scanner warning engineers when modified files caused past production outages |
| **Demo Video Script** | `docs/DEMO_VIDEO_SCRIPT.md` | 3-minute video presentation script with timestamps and presenter cues |
| **Pitch Presentation**| `docs/SLIDES.md` | 12-slide hackathon pitch deck outline and speaking points |
| **Team Dossier** | `docs/TEAM_SPLIT.md` | 6-member delegation breakdown and verification matrix |

---

## 🛡️ Proactive Code Memory (`pr-check`)
Before risky code ever deploys to production, the PR scanner analyzes modified files and git diffs:
1. Identifies files that previously caused production incidents (`role: root_cause` vs `involved`).
2. Computes embedding similarity against historical fix commits.
3. Produces actionable checklists advising developers what edge-cases to double-check.

---

## 🧪 Verification & Acceptance Tests

```bash
# 1. Verify Slack bot and FastAPI healthz unit/integration tests
PYTHONPATH="" .venv/bin/pytest tests/unit/test_slack_bot.py tests/integration/test_healthz.py -v

# 2. Run proactive PR risk scanner against checkout OrderClient
PYTHONPATH="" .venv/bin/python -m app.cli pr-check --files services/checkout/OrderClient.py
```

---

## 🎤 Presentation & Demo Role
- **Scene 4 Co-presenter (1:45 - 2:15):** Demonstrating the proactive `pr-check` command warning a developer before deploying risky code.
- **Coordination:** Video recording, audio syncing, and Devpost submission checklist.
