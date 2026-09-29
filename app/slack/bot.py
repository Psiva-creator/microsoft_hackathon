import json
import re
from typing import Any

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.agent.investigate import investigate
from app.agent.postmortem import confirm_and_save_to_memory, resolve_incident
from app.config import get_settings
from app.core.redact import redact
from app.db import get_db
from app.logging import get_logger
from app.memory.stats import record_feedback
from app.memory.working import append_event, init_live_incident
from app.models import Analysis, LiveEvent

logger = get_logger(__name__)

# Map thread_ts -> live_id for fast thread tracking
THREAD_TO_INCIDENT: dict[str, str] = {}


def build_analysis_blocks(analysis: Analysis, live_id: str) -> list[dict[str, Any]]:
    """Builds Slack Block Kit components for structured incident analysis."""
    top_conf = analysis.hypotheses[0].confidence.upper() if analysis.hypotheses else "LOW"
    conf_badge = (
        "🟢 *HIGH CONFIDENCE*"
        if top_conf == "HIGH"
        else ("🟡 *MEDIUM CONFIDENCE*" if top_conf == "MEDIUM" else "🔴 *LOW CONFIDENCE*")
    )

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚨 Incident Analysis: {live_id}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Confidence:* {conf_badge}\n*Summary:* {redact(analysis.summary)}",
            },
        },
        {"type": "divider"},
    ]

    for idx, hyp in enumerate(analysis.hypotheses[:3], 1):
        hyp_text = f"*Hypothesis {idx}:* {hyp.cause} (Confidence: `{hyp.confidence.upper()}`)\n"
        if hyp.evidence_for:
            hyp_text += "*Evidence For:*\n" + "\n".join(f"  • {e}" for e in hyp.evidence_for) + "\n"
        if hyp.evidence_against:
            hyp_text += "*Evidence Against:*\n" + "\n".join(f"  • {e}" for e in hyp.evidence_against) + "\n"
        if hyp.recommended_steps:
            hyp_text += "*Recommended Steps (Safest First):*\n" + "\n".join(
                f"  {s_idx}. {s}" for s_idx, s in enumerate(hyp.recommended_steps, 1)
            ) + "\n"
        if hyp.runbook_id:
            hyp_text += f"*Runbook:* `{hyp.runbook_id}`\n"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": redact(hyp_text)},
        })

    # Pattern Separation & Similar Precedents
    similar_blocks = []
    for hyp in analysis.hypotheses:
        for sim in hyp.similar_incidents:
            similar_blocks.append(
                f"• *{sim.id}*: {sim.why_similar}\n  _Differences:_ {sim.differences}"
            )

    if similar_blocks:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🧠 Similar Past Incidents & Pattern Separation:*\n" + "\n".join(similar_blocks[:3]),
            },
        })

    if analysis.needs_human_decision:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "⚠️ *Requires Human Authorization (Read-Only Safety Guard):*\n"
                + "\n".join(f"  🛑 {item}" for item in analysis.needs_human_decision),
            },
        })

    blocks.append({"type": "divider"})

    # Action Buttons
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👍 Helpful"},
                "style": "primary",
                "action_id": "feedback_helpful",
                "value": live_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👎 Not Helpful"},
                "style": "danger",
                "action_id": "feedback_unhelpful",
                "value": live_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔍 Re-investigate"},
                "action_id": "reinvestigate",
                "value": live_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Mark Resolved"},
                "action_id": "mark_resolved",
                "value": live_id,
            },
        ],
    })

    return blocks


def build_resolve_modal(live_id: str) -> dict[str, Any]:
    """Builds Slack Modal for human incident resolution."""
    return {
        "type": "modal",
        "callback_id": "resolve_incident_modal",
        "private_metadata": live_id,
        "title": {"type": "plain_text", "text": "Resolve Incident"},
        "submit": {"type": "plain_text", "text": "Draft Post-Mortem"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "root_cause_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "root_cause_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Describe the verified root cause..."},
                },
                "label": {"type": "plain_text", "text": "Root Cause"},
            },
            {
                "type": "input",
                "block_id": "steps_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "steps_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "List the steps taken to restore service (one per line)..."},
                },
                "label": {"type": "plain_text", "text": "Resolution Steps"},
            },
            {
                "type": "input",
                "block_id": "runbooks_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "runbooks_input",
                    "placeholder": {"type": "plain_text", "text": "e.g. RB-db-pool-exhaustion"},
                },
                "label": {"type": "plain_text", "text": "Runbooks Consulted"},
            },
            {
                "type": "input",
                "block_id": "worked_block",
                "element": {
                    "type": "radio_buttons",
                    "action_id": "worked_input",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Yes, resolution worked completely"},
                            "value": "yes",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Partially worked"},
                            "value": "partly",
                        },
                        {
                            "text": {"type": "plain_text", "text": "No, fix failed or rolled back"},
                            "value": "no",
                        },
                    ],
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Yes, resolution worked completely"},
                        "value": "yes",
                    },
                },
                "label": {"type": "plain_text", "text": "Did the suggested fix work?"},
            },
        ],
    }


def create_slack_app() -> App:
    """Initializes the Slack Bolt application with Socket Mode handlers."""
    settings = get_settings()
    app = App(
        token=settings.SLACK_BOT_TOKEN or "xoxb-mock-token",
        signing_secret="mock-secret",
        token_verification_enabled=bool(settings.SLACK_BOT_TOKEN),
    )

    @app.event("app_mention")
    def handle_mention(event: dict[str, Any], say: Any, client: Any) -> None:
        if event.get("bot_id"):
            return

        text = event.get("text", "")
        clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
        ts = event.get("thread_ts", event["ts"])

        # Check if already tracking this thread
        live_id = THREAD_TO_INCIDENT.get(ts)
        if not live_id:
            live_id = init_live_incident(
                title=clean_text[:60] or "Slack Incident",
                services=[],
                description=clean_text,
            )
            THREAD_TO_INCIDENT[ts] = live_id

        # Append mention event to Redis working memory
        append_event(
            live_id=live_id,
            event=LiveEvent(
                type="message",
                data={"user": event.get("user", "slack_user"), "text": clean_text},
            ),
        )

        say(
            text=f"🔍 Investigating live incident `{live_id}`... recalling precedents and querying read-only telemetry.",
            thread_ts=ts,
        )

        # Run Claude investigation
        analysis = investigate(live_id=live_id)
        blocks = build_analysis_blocks(analysis, live_id=live_id)
        say(blocks=blocks, text=analysis.summary, thread_ts=ts)

    @app.event("message")
    def handle_message(event: dict[str, Any], say: Any) -> None:
        if event.get("bot_id"):
            return

        ts = event.get("thread_ts")
        if not ts or ts not in THREAD_TO_INCIDENT:
            return

        live_id = THREAD_TO_INCIDENT[ts]
        text = event.get("text", "")

        append_event(
            live_id=live_id,
            event=LiveEvent(
                type="message",
                data={"user": event.get("user", "slack_user"), "text": text},
            ),
        )

        if "/reinvestigate" in text:
            say(text="🔄 Re-investigating with new context...", thread_ts=ts)
            analysis = investigate(live_id=live_id)
            blocks = build_analysis_blocks(analysis, live_id=live_id)
            say(blocks=blocks, text=analysis.summary, thread_ts=ts)

    @app.command("/incident")
    def handle_slash_incident(ack: Any, command: dict[str, Any], say: Any) -> None:
        ack()
        text = command.get("text", "").strip()
        live_id = init_live_incident(
            title=text[:60] or "Incident via /incident",
            services=[],
            description=text,
        )
        say(text=f"🚨 New Incident `{live_id}` started: *{text}*")
        analysis = investigate(live_id=live_id)
        blocks = build_analysis_blocks(analysis, live_id=live_id)
        say(blocks=blocks, text=analysis.summary)

    @app.action("feedback_helpful")
    def handle_helpful(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        live_id = body["actions"][0]["value"]
        logger.info("slack_feedback_helpful", live_id=live_id)
        record_feedback(suggestion_id=None, runbook_id=None, helpful=True, user_ref=body.get("user", {}).get("id"))
        respond(text="🙏 Thank you for the feedback! Reinforced procedural runbook memory.", replace_original=False)

    @app.action("feedback_unhelpful")
    def handle_unhelpful(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        live_id = body["actions"][0]["value"]
        logger.info("slack_feedback_unhelpful", live_id=live_id)
        record_feedback(suggestion_id=None, runbook_id=None, helpful=False, user_ref=body.get("user", {}).get("id"))
        respond(text="📝 Noted. Down-weighted associated runbook precedence.", replace_original=False)

    @app.action("reinvestigate")
    def handle_reinvestigate_button(ack: Any, body: dict[str, Any], say: Any) -> None:
        ack()
        live_id = body["actions"][0]["value"]
        ts = body["message"].get("thread_ts", body["message"]["ts"])

        say(text=f"🔄 Re-running investigation for `{live_id}`...", thread_ts=ts)
        analysis = investigate(live_id=live_id)
        blocks = build_analysis_blocks(analysis, live_id=live_id)
        say(blocks=blocks, text=analysis.summary, thread_ts=ts)

    @app.action("mark_resolved")
    def handle_mark_resolved_button(ack: Any, body: dict[str, Any], client: Any) -> None:
        ack()
        live_id = body["actions"][0]["value"]
        modal = build_resolve_modal(live_id=live_id)
        client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.view("resolve_incident_modal")
    def handle_modal_submission(ack: Any, body: dict[str, Any], client: Any, say: Any) -> None:
        ack()
        live_id = body["view"]["private_metadata"]
        values = body["view"]["state"]["values"]

        root_cause = values["root_cause_block"]["root_cause_input"]["value"]
        steps_raw = values["steps_block"]["steps_input"]["value"]
        steps = [s.strip() for s in steps_raw.splitlines() if s.strip()]

        rb_raw = values.get("runbooks_block", {}).get("runbooks_input", {}).get("value") or ""
        runbook_ids = [r.strip() for r in rb_raw.split(",") if r.strip()]

        worked_val = values["worked_block"]["worked_input"]["selected_option"]["value"]
        worked = worked_val in ("yes", "partly")

        draft = resolve_incident(
            live_id=live_id,
            root_cause=root_cause,
            steps=steps,
            runbook_ids=runbook_ids,
            worked=worked,
        )

        # Post post-mortem draft with confirmation buttons
        postmortem_blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📋 Post-Mortem Draft: {live_id}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": draft.markdown[:2500]},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💾 Approve & Save to Memory"},
                        "style": "primary",
                        "action_id": "postmortem_approve",
                        "value": live_id,
                    },
                ],
            },
        ]

        # Find thread if available
        thread_ts = None
        for t_ts, l_id in THREAD_TO_INCIDENT.items():
            if l_id == live_id:
                thread_ts = t_ts
                break

        say(blocks=postmortem_blocks, text="Post-Mortem Draft Ready", thread_ts=thread_ts)

    @app.action("postmortem_approve")
    def handle_postmortem_approve(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        live_id = body["actions"][0]["value"]
        draft_md = f"# Post-Mortem: Incident {live_id}\n\nResolved via Slack."
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT postmortem_draft FROM live_incidents WHERE id = %s", (live_id,))
                    row = cur.fetchone()
                    if row and row.get("postmortem_draft"):
                        pm_draft = row["postmortem_draft"]
                        if isinstance(pm_draft, str):
                            pm_draft = json.loads(pm_draft)
                        if isinstance(pm_draft, dict):
                            draft_md = pm_draft.get("markdown", draft_md)
        except Exception as e:
            logger.warning("fetch_postmortem_draft_failed", live_id=live_id, error=str(e))

        inc_id = confirm_and_save_to_memory(live_id=live_id, approved_markdown=draft_md)
        respond(
            text=f"🎉 *Post-mortem approved!* Incident committed to long-term episodic memory as `{inc_id}`. Runbook statistics updated.",
            replace_original=False,
        )

    return app


def start_slack_bot() -> None:
    """Starts the Slack bot in Socket Mode."""
    settings = get_settings()
    if not settings.SLACK_APP_TOKEN or not settings.SLACK_BOT_TOKEN:
        logger.warning("slack_tokens_missing_bot_disabled")
        return

    app = create_slack_app()
    handler = SocketModeHandler(app, settings.SLACK_APP_TOKEN)
    logger.info("starting_slack_bot_socket_mode")
    handler.start()
