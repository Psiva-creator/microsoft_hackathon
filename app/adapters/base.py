from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LogLine:
    timestamp: str
    level: str
    message: str


@dataclass
class MetricPoint:
    timestamp: str
    value: float


@dataclass
class DeployEvent:
    service: str
    version: str
    deployed_at: str
    commit_sha: str
    author: str
    status: str


@dataclass
class CommitInfo:
    sha: str
    author: str
    date: str
    message: str
    files: list[str] = field(default_factory=list)


class LogAdapter(Protocol):
    def query(
        self, service: str, query: str, minutes: int = 30, limit: int = 50
    ) -> list[LogLine]: ...


class MetricsAdapter(Protocol):
    def query(self, service: str, metric: str, minutes: int = 60) -> list[MetricPoint]: ...


class DeployAdapter(Protocol):
    def recent(self, service: str, hours: int = 6) -> list[DeployEvent]: ...


class CodeAdapter(Protocol):
    def commit(self, sha: str) -> CommitInfo | None: ...

    def history(self, file_path: str, limit: int = 10) -> list[CommitInfo]: ...
