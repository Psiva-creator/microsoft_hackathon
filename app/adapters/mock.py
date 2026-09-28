import json
from pathlib import Path

from app.adapters.base import CommitInfo, DeployEvent, LogLine, MetricPoint
from app.config import get_settings
from app.core.redact import redact


class MockLogAdapter:
    def __init__(self, scenario_dir: Path):
        self.scenario_dir = scenario_dir

    def query(
        self, service: str, query: str = "", minutes: int = 30, limit: int = 50
    ) -> list[LogLine]:
        logs_file = self.scenario_dir / "logs.jsonl"
        results: list[LogLine] = []
        if not logs_file.exists():
            return results

        q = query.lower()
        with open(logs_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    msg = data.get("message", "")
                    if not q or q in msg.lower():
                        results.append(
                            LogLine(
                                timestamp=data.get("timestamp", ""),
                                level=data.get("level", "INFO"),
                                message=redact(msg),
                            )
                        )
                except Exception:
                    continue
                if len(results) >= limit:
                    break
        return results


class MockMetricsAdapter:
    def __init__(self, scenario_dir: Path):
        self.scenario_dir = scenario_dir

    def query(self, service: str, metric: str = "", minutes: int = 60) -> list[MetricPoint]:
        metrics_file = self.scenario_dir / "metrics.json"
        if not metrics_file.exists():
            return []

        try:
            data = json.loads(metrics_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                points = data.get("points", [])
                return [
                    MetricPoint(timestamp=p["timestamp"], value=float(p["value"])) for p in points
                ]
        except Exception:
            pass
        return []


class MockDeployAdapter:
    def __init__(self, scenario_dir: Path):
        self.scenario_dir = scenario_dir

    def recent(self, service: str = "", hours: int = 6) -> list[DeployEvent]:
        deploys_file = self.scenario_dir / "deploys.json"
        if not deploys_file.exists():
            return []

        try:
            data = json.loads(deploys_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [DeployEvent(**item) for item in data]
        except Exception:
            pass
        return []


class MockCodeAdapter:
    def __init__(self, scenario_dir: Path):
        self.scenario_dir = scenario_dir

    def commit(self, sha: str) -> CommitInfo | None:
        commits_file = self.scenario_dir / "commits.json"
        if not commits_file.exists():
            return None
        try:
            data = json.loads(commits_file.read_text(encoding="utf-8"))
            for item in data:
                if item.get("sha") == sha:
                    return CommitInfo(**item)
        except Exception:
            pass
        return None

    def history(self, file_path: str, limit: int = 10) -> list[CommitInfo]:
        commits_file = self.scenario_dir / "commits.json"
        if not commits_file.exists():
            return []
        try:
            data = json.loads(commits_file.read_text(encoding="utf-8"))
            results = []
            for item in data:
                files = item.get("files", [])
                if any(file_path in f for f in files):
                    results.append(CommitInfo(**item))
            return results[:limit]
        except Exception:
            return []


def resolve_scenario_dir(scenario_name: str) -> Path:
    base = Path("data/mock_env/scenarios")
    direct = base / scenario_name
    if direct.exists() and direct.is_dir():
        return direct
    if base.exists():
        for p in base.iterdir():
            if p.is_dir() and (
                scenario_name.lower() in p.name.lower() or p.name.lower() in scenario_name.lower()
            ):
                return p
    return direct


def get_mock_adapters(
    scenario_name: str | None = None,
) -> tuple[MockLogAdapter, MockMetricsAdapter, MockDeployAdapter, MockCodeAdapter]:
    settings = get_settings()
    name = scenario_name or settings.MOCK_SCENARIO
    scenario_dir = resolve_scenario_dir(name)

    return (
        MockLogAdapter(scenario_dir),
        MockMetricsAdapter(scenario_dir),
        MockDeployAdapter(scenario_dir),
        MockCodeAdapter(scenario_dir),
    )
