import re
from pathlib import Path

import git

from app.core.embeddings import get_embedder
from app.db import get_db
from app.logging import get_logger

logger = get_logger(__name__)


def parse_diff_function_names(diff_text: str) -> list[str]:
    """Parses touched function/context names from hunk headers (@@ ... @@ function_name)."""
    func_names: list[str] = []
    pattern = re.compile(r"@@\s+-[0-9,]+\s+\+[0-9,]+\s+@@\s*(.*)")
    for line in diff_text.splitlines():
        m = pattern.match(line)
        if m:
            ctx = m.group(1).strip()
            if ctx:
                func_names.append(ctx)
    return list(set(func_names))


def index_repo(repo_path: str | Path, since: str | None = None) -> int:
    """Indexes Git commits, changed files, and touched functions into code_changes."""
    repo = git.Repo(repo_path)
    embedder = get_embedder()
    count = 0

    commits = list(repo.iter_commits(since=since, max_count=50))
    for commit in commits:
        sha = commit.hexsha
        author = commit.author.email if commit.author else "unknown"
        committed_at = commit.committed_datetime.isoformat()
        message = commit.message.strip()

        # Extract stats and files
        files = list(commit.stats.files.keys())

        # Generate embedding for message + files
        emb_text = f"{message}\nFiles: {', '.join(files)}"
        emb = embedder.embed_documents([emb_text])[0]

        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO code_changes (repo, commit_sha, author, committed_at, message, files, emb)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (repo, commit_sha) DO NOTHING;
                        """,
                        (str(repo_path), sha, author, committed_at, message, files, emb),
                    )
                    conn.commit()
            count += 1
        except Exception as e:
            logger.warning("index_commit_failed", sha=sha, error=str(e))

    logger.info("indexed_commits", count=count, repo=str(repo_path))
    return count
