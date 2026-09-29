import json
from pathlib import Path

import pytest

from app.ingestion.loaders import (
    RawDoc,
    load_folder,
    load_jira_export,
    load_jira_file,
    load_slack_export,
    load_slack_transcript_txt,
)
from app.ingestion.pipeline import process_raw_doc
from app.memory.store import (
    clear_in_memory_store,
    find_incident_by_doc_hash,
    get_incident,
    get_incident_count,
)


@pytest.fixture(autouse=True)
def clean_store():
    """Ensure in-memory store is isolated between tests."""
    clear_in_memory_store()
    yield
    clear_in_memory_store()


def test_load_diverse_64_seed_documents():
    """Confirms all 64 diverse incident documents in data/seed are loaded."""
    seed_path = Path("data/seed")
    assert seed_path.exists(), "data/seed directory must exist"

    docs = list(load_folder(seed_path))
    assert len(docs) == 64

    types = {d.source_type for d in docs}
    assert "markdown" in types
    assert "jira" in types
    assert "slack" in types

    # Count breakdown
    md_count = sum(1 for d in docs if d.source_type == "markdown")
    jira_count = sum(1 for d in docs if d.source_type == "jira")
    slack_count = sum(1 for d in docs if d.source_type == "slack")

    assert md_count == 33
    assert jira_count == 15
    assert slack_count == 16


def test_load_jira_single_and_bulk(tmp_path: Path):
    # Single ticket JSON
    single_ticket = {
        "key": "OPS-9001",
        "summary": "Database connectivity loss in checkout-api",
        "description": "Timeout when acquiring pool connection.",
        "comments": [{"author": "alice", "body": "Checked pgbouncer pool."}],
    }
    single_file = tmp_path / "single.json"
    single_file.write_text(json.dumps(single_ticket), encoding="utf-8")

    single_docs = list(load_jira_file(single_file))
    assert len(single_docs) == 1
    assert single_docs[0].source_id == "OPS-9001"
    assert "checkout-api" in single_docs[0].text
    assert "alice" in single_docs[0].text

    # Bulk export JSON with issues list
    bulk_export = {
        "issues": [
            {
                "key": "OPS-9002",
                "fields": {
                    "summary": "Auth token verification failure",
                    "description": "Expired signing key in auth-service",
                    "comment": {"comments": [{"author": "bob", "body": "Rotated secret"}]},
                },
            },
            {
                "key": "OPS-9003",
                "fields": {
                    "summary": "Kafka consumer lag alert",
                    "description": "Slow consumer group in orders-service",
                },
            },
        ]
    }
    bulk_file = tmp_path / "bulk.json"
    bulk_file.write_text(json.dumps(bulk_export), encoding="utf-8")

    bulk_docs = list(load_jira_export(bulk_file))
    assert len(bulk_docs) == 2
    assert bulk_docs[0].source_id == "OPS-9002"
    assert bulk_docs[1].source_id == "OPS-9003"


def test_load_slack_txt_and_json(tmp_path: Path):
    # Plain text transcript
    transcript = (
        "[14:02:11] @channel Alert: payments-gateway error rate high\n"
        "[14:03:00] @carol: Seeing 502s from upstream bank gateway\n"
        "[14:07:30] @dave: Mitigated by failover to backup provider\n"
    )
    txt_file = tmp_path / "inc_slack.txt"
    txt_file.write_text(transcript, encoding="utf-8")

    txt_docs = list(load_slack_transcript_txt(txt_file))
    assert len(txt_docs) == 1
    assert txt_docs[0].source_type == "slack"
    assert "payments-gateway" in txt_docs[0].text

    # Slack JSON export format
    slack_json = [
        {
            "ts": "1720000000.000100",
            "user": "U123",
            "text": "Outage in inventory-service redis cluster!",
        },
        {
            "ts": "1720000060.000200",
            "thread_ts": "1720000000.000100",
            "user": "U456",
            "text": "Failover in progress.",
        },
    ]
    json_file = tmp_path / "incidents" / "2026-07-15.json"
    json_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(slack_json), encoding="utf-8")

    json_docs = list(load_slack_export(json_file))
    assert len(json_docs) == 1
    assert json_docs[0].source_type == "slack"
    assert "inventory-service" in json_docs[0].text


def test_sha256_exact_deduplication():
    doc = RawDoc(
        source_type="markdown",
        source_id="inc_pool.md",
        text="# Incident: Database Connection Pool Exhaustion\ncheckout-api failed with pool exhaustion.",
        metadata={"services": ["checkout-api"]},
    )

    id1 = process_raw_doc(doc)
    assert id1 is not None
    assert get_incident_count() == 1

    # Ingest the exact same document again
    id2 = process_raw_doc(doc)
    assert id2 == id1
    # Count must remain 1 (no duplicate inserted)
    assert get_incident_count() == 1


def test_near_duplicate_cosine_matching_and_merge():
    # Original incident from seed data
    t1 = Path("data/seed/inc_0007_connection_pool.md").read_text(encoding="utf-8")
    t2 = Path("data/seed/inc_0061_dupe_0007.md").read_text(encoding="utf-8")

    doc1 = RawDoc(
        source_type="markdown",
        source_id="inc_0007_connection_pool.md",
        text=t1,
        metadata={"services": ["checkout-api", "postgres-primary"]},
    )
    id1 = process_raw_doc(doc1)
    assert id1 == "INC-0001"
    assert get_incident_count() == 1

    # Near-duplicate incident (cosine similarity >= 0.97 on same services)
    doc2 = RawDoc(
        source_type="markdown",
        source_id="inc_0061_dupe_0007.md",
        text=t2,
        metadata={"services": ["checkout-api", "postgres-primary"]},
    )

    # Ingesting near-duplicate should merge into INC-0001
    id2 = process_raw_doc(doc2)
    assert id2 == id1
    assert get_incident_count() == 1

    # Verify that the merged incident now recognizes doc2's SHA-256
    import hashlib

    doc2_sha = hashlib.sha256(doc2.text.strip().encode("utf-8")).hexdigest()
    matched_id = find_incident_by_doc_hash(doc2_sha)
    assert matched_id == id1

    # Third ingestion of doc2 hits the exact SHA-256 check
    id3 = process_raw_doc(doc2)
    assert id3 == id1
    assert get_incident_count() == 1


def test_near_duplicate_preserves_longer_root_cause():
    t1 = Path("data/seed/inc_0007_connection_pool.md").read_text(encoding="utf-8")
    t2 = Path("data/seed/inc_0061_dupe_0007.md").read_text(encoding="utf-8")

    # Add extended diagnostic root-cause explanation to t2
    detailed_cause = (
        "Root cause was database connection pool exhaustion in submit() method "
        "aggravated by orphaned connections and connection leak detection thresholds missing."
    )
    t2_expanded = t2 + f"\n\n## Extended Diagnostic\nRoot Cause: {detailed_cause}"

    doc1 = RawDoc(
        source_type="markdown",
        source_id="inc_0007.md",
        text=t1,
        metadata={"services": ["checkout-api", "postgres-primary"]},
    )
    id1 = process_raw_doc(doc1)

    doc2 = RawDoc(
        source_type="markdown",
        source_id="inc_0061.md",
        text=t2_expanded,
        metadata={"services": ["checkout-api", "postgres-primary"]},
    )
    id2 = process_raw_doc(doc2)
    assert id2 == id1

    inc = get_incident(id1)
    assert inc is not None
    # Must preserve the more comprehensive root cause explanation
    assert "connection leak detection thresholds missing" in inc["root_cause"]
