import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator


@dataclass
class RawDoc:
    source_type: str  # markdown, jira, slack, notion, postmortem
    source_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def load_folder(folder_path: str | Path) -> Generator[RawDoc, None, None]:
    p = Path(folder_path)
    if not p.exists():
        return

    for file_path in sorted(p.iterdir()):
        if file_path.is_file():
            if file_path.name.startswith("_"):
                continue  # skip metadata like _labels.json

            suffix = file_path.suffix.lower()
            if suffix == ".json":
                try:
                    content = file_path.read_text(encoding="utf-8")
                    data = json.loads(content)
                    if isinstance(data, dict) and ("key" in data or "summary" in data):
                        yield from load_jira_file(file_path)
                    else:
                        yield RawDoc(
                            source_type="json",
                            source_id=file_path.name,
                            text=content,
                            metadata={"file_path": str(file_path)},
                        )
                except Exception:
                    continue
            elif suffix == ".txt":
                content = file_path.read_text(encoding="utf-8")
                yield RawDoc(
                    source_type="slack" if "slack" in file_path.name else "txt",
                    source_id=file_path.name,
                    text=content,
                    metadata={"file_path": str(file_path)},
                )
            elif suffix in (".md", ".markdown"):
                content = file_path.read_text(encoding="utf-8")
                yield RawDoc(
                    source_type="markdown",
                    source_id=file_path.name,
                    text=content,
                    metadata={"file_path": str(file_path)},
                )


def load_jira_file(file_path: Path) -> Generator[RawDoc, None, None]:
    content = file_path.read_text(encoding="utf-8")
    data = json.loads(content)
    ticket_id = data.get("key", file_path.stem)
    summary = data.get("summary", "")
    description = data.get("description", "")
    comments = data.get("comments", [])
    comments_text = "\n".join(f"- {c.get('author', 'user')}: {c.get('body', '')}" for c in comments)

    full_text = f"Ticket: {ticket_id}\nSummary: {summary}\nDescription: {description}\nComments:\n{comments_text}"
    yield RawDoc(
        source_type="jira",
        source_id=ticket_id,
        text=full_text,
        metadata={"key": ticket_id, "file_path": str(file_path)},
    )


def load_slack_export(path: str | Path) -> Generator[RawDoc, None, None]:
    p = Path(path)
    if not p.exists():
        return
    for f in p.glob("**/*.json"):
        content = f.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, list):
            # Slack export format: list of messages
            thread_messages: list[str] = []
            is_incident = False
            for msg in data:
                text = msg.get("text", "")
                if any(k in text.lower() for k in ("incident", "outage", "sev")):
                    is_incident = True
                user = msg.get("user", "user")
                thread_messages.append(f"{user}: {text}")
            if is_incident and thread_messages:
                yield RawDoc(
                    source_type="slack",
                    source_id=f.stem,
                    text="\n".join(thread_messages),
                    metadata={"channel": f.parent.name},
                )
