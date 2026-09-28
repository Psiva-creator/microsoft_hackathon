import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator

from app.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RawDoc:
    source_type: str  # markdown, jira, slack, notion, json, txt
    source_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def load_jira_file(file_path: Path) -> Generator[RawDoc, None, None]:
    """Loads a single Jira issue JSON or bulk export file."""
    content = file_path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
    except Exception as e:
        logger.warning("jira_json_parse_error", file=str(file_path), error=str(e))
        return

    # Case 1: Bulk export containing 'issues' array (Jira Cloud/Server API export)
    if isinstance(data, dict) and "issues" in data and isinstance(data["issues"], list):
        for issue in data["issues"]:
            yield from _parse_jira_issue_dict(issue, str(file_path))
        return

    # Case 2: Array of tickets
    if isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                yield from _parse_jira_issue_dict(item, f"{file_path.stem}_{idx}")
        return

    # Case 3: Single ticket dictionary
    if isinstance(data, dict):
        yield from _parse_jira_issue_dict(data, file_path.stem, file_path=str(file_path))


def _parse_jira_issue_dict(
    data: dict[str, Any],
    fallback_id: str,
    file_path: str = "",
) -> Generator[RawDoc, None, None]:
    """Extracts a standardized RawDoc from a Jira issue dictionary."""
    ticket_id = data.get("key") or fallback_id

    # Check if standard or nested 'fields' structure
    fields = data.get("fields", data)
    summary = fields.get("summary", "")
    description = fields.get("description", "")
    if isinstance(description, dict):  # Atlassian Document Format (ADF)
        description = json.dumps(description)

    comments_raw = fields.get("comments") or (fields.get("comment", {}).get("comments", []))
    comments_lines = []
    if isinstance(comments_raw, list):
        for c in comments_raw:
            if isinstance(c, dict):
                raw_author = c.get("author")
                if isinstance(raw_author, dict):
                    author = raw_author.get("displayName") or raw_author.get("name") or "user"
                elif isinstance(raw_author, str):
                    author = raw_author
                else:
                    author = "user"
                body = c.get("body", "")
                if isinstance(body, dict):
                    body = json.dumps(body)
                comments_lines.append(f"- {author}: {body}")
            elif isinstance(c, str):
                comments_lines.append(f"- {c}")

    comments_text = "\n".join(comments_lines)
    full_text = f"Ticket: {ticket_id}\nSummary: {summary}\nDescription: {description}\nComments:\n{comments_text}".strip()

    meta = {
        "key": ticket_id,
        "summary": summary,
        "status": fields.get("status", {}).get("name") if isinstance(fields.get("status"), dict) else fields.get("status"),
        "resolution": fields.get("resolution", {}).get("name") if isinstance(fields.get("resolution"), dict) else fields.get("resolution"),
    }
    if file_path:
        meta["file_path"] = file_path

    yield RawDoc(
        source_type="jira",
        source_id=ticket_id,
        text=full_text,
        metadata=meta,
    )


def load_jira_export(path: str | Path) -> Generator[RawDoc, None, None]:
    """Loads all Jira exports from a file or folder."""
    p = Path(path)
    if not p.exists():
        return
    if p.is_file():
        yield from load_jira_file(p)
    else:
        for f in sorted(p.glob("**/*.json")):
            yield from load_jira_file(f)


def load_slack_transcript_txt(file_path: Path) -> Generator[RawDoc, None, None]:
    """Loads a Slack conversation transcript from a text file."""
    content = file_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return

    # Check if lines look like chat messages [HH:MM] user: ... or user: ...
    is_slack = any(
        re.match(r"^\[\d{2}:\d{2}(?::\d{2})?\]", l) or "@channel" in l or "@here" in l
        for l in lines
    )
    source_type = "slack" if is_slack or "slack" in file_path.stem.lower() else "txt"

    yield RawDoc(
        source_type=source_type,
        source_id=file_path.name,
        text=content,
        metadata={"file_path": str(file_path), "line_count": len(lines)},
    )


def load_slack_export(path: str | Path) -> Generator[RawDoc, None, None]:
    """Loads Slack workspace JSON exports, grouping threaded messages into incident documents."""
    p = Path(path)
    if not p.exists():
        return

    files = [p] if p.is_file() else sorted(p.glob("**/*.json"))
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception as e:
            logger.warning("slack_json_parse_error", file=str(f), error=str(e))
            continue

        if not isinstance(data, list):
            continue

        # Group messages by thread_ts if available, otherwise by channel day
        threads: dict[str, list[dict[str, Any]]] = {}
        channel_name = f.parent.name

        for msg in data:
            if not isinstance(msg, dict):
                continue
            thread_key = msg.get("thread_ts") or msg.get("ts") or "default"
            threads.setdefault(thread_key, []).append(msg)

        incident_keywords = ("incident", "outage", "sev", "alert", "p0", "p1", "down", "error")

        for thread_id, msgs in threads.items():
            thread_lines: list[str] = []
            has_incident_cue = any(k in channel_name.lower() for k in ("incident", "outage", "sev"))

            for msg in msgs:
                text = msg.get("text", "")
                if any(k in text.lower() for k in incident_keywords):
                    has_incident_cue = True
                user = msg.get("user", "user")
                ts = msg.get("ts", "")
                thread_lines.append(f"[{ts}] {user}: {text}")

            if has_incident_cue and thread_lines:
                doc_id = f"{f.stem}_{thread_id.replace('.', '_')}"
                yield RawDoc(
                    source_type="slack",
                    source_id=doc_id,
                    text="\n".join(thread_lines),
                    metadata={"channel": channel_name, "thread_ts": thread_id, "file_path": str(f)},
                )


def load_notion_confluence_md(path: str | Path) -> Generator[RawDoc, None, None]:
    """Loads exported markdown documentation from Notion or Confluence."""
    p = Path(path)
    if not p.exists():
        return

    files = [p] if p.is_file() else sorted(p.glob("**/*.md"))
    for f in files:
        content = f.read_text(encoding="utf-8")
        yield RawDoc(
            source_type="markdown",
            source_id=f.name,
            text=content,
            metadata={"file_path": str(f)},
        )


def load_folder(folder_path: str | Path) -> Generator[RawDoc, None, None]:
    """Traverses a directory and yields RawDoc instances for all supported incident formats."""
    p = Path(folder_path)
    if not p.exists():
        return

    for file_path in sorted(p.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.name.startswith("_"):
            continue  # skip metadata like _labels.json

        suffix = file_path.suffix.lower()
        if suffix == ".json":
            try:
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if isinstance(data, dict) and ("key" in data or "summary" in data or "issues" in data):
                    yield from load_jira_file(file_path)
                elif isinstance(data, list):
                    # Could be slack export or list of jira tickets
                    if any("user" in item and "text" in item for item in data if isinstance(item, dict)):
                        yield from load_slack_export(file_path)
                    else:
                        yield from load_jira_file(file_path)
                else:
                    yield RawDoc(
                        source_type="json",
                        source_id=file_path.name,
                        text=content,
                        metadata={"file_path": str(file_path)},
                    )
            except Exception as e:
                logger.warning("file_load_failed", path=str(file_path), error=str(e))
                continue

        elif suffix == ".txt":
            yield from load_slack_transcript_txt(file_path)

        elif suffix in (".md", ".markdown"):
            content = file_path.read_text(encoding="utf-8")
            yield RawDoc(
                source_type="markdown",
                source_id=file_path.name,
                text=content,
                metadata={"file_path": str(file_path)},
            )
