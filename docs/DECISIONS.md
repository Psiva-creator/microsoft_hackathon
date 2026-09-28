# Architectural and Design Decisions (ADR)

This file records key decisions, trade-offs, and clarifications made during implementation.

## ADR-001: Technology Stack and Driver Selection
- **Context**: The project requires high-performance vector search in PostgreSQL and low-latency working memory in Redis.
- **Decision**: Use `psycopg` v3 with `psycopg_pool.ConnectionPool` and `pgvector.psycopg.register_vector` instead of an ORM. Use `redis-py` for working memory.
- **Rationale**: Plain SQL gives explicit control over vector similarity queries (`<=>` cosine operator), HNSW index parameter tuning (`hnsw.ef_search`), and full-text search rankings (`ts_rank_cd`).

## ADR-002: Dual Embedding Strategy
- **Context**: On-call engineers start with incomplete symptoms, but pattern discovery needs complete post-mortem context.
- **Decision**: Store `emb_symptom` (title, symptoms, normalized errors, services) for live query matching, and `emb_full` (symptoms + root cause + resolution steps + lessons) for clustering into patterns.
- **Rationale**: Models the brain's pattern completion: partial cues retrieve full memories without requiring the responder to already know the root cause.

## ADR-003: Safety and Read-Only Policy
- **Context**: An on-call assistant must not accidentally disrupt production.
- **Decision**: Hardcode `ALLOW_ACTIONS=false` in v1; all adapter tools are strictly read-only query interfaces. Any destructive or state-changing action is routed to `needs_human_decision`.
- **Rationale**: Eliminates the risk of automated remediation catastrophes during high-stress outages.
