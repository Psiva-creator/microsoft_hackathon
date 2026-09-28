---
id: RB-db-pool-exhaustion
title: Database Connection Pool Exhaustion Recovery
services: [checkout-api, orders-service, inventory-service, postgres-primary]
---

# RB-db-pool-exhaustion: Database Connection Pool Exhaustion Recovery

## Symptoms
- HTTP 503 or 504 errors on API endpoints querying Postgres.
- Error logs stating: `HikariPool - Connection is not available, request timed out after 30000ms`.
- High database connection count near `max_connections`.
- P99 latency spikes across dependent services.

## Verification Steps
1. Check pool metrics for active vs. idle connections:
   ```bash
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
2. Verify if a recent deployment introduced connection leaks or missing connection close calls:
   ```bash
   git log -n 5 --stat
   ```
3. Check long-running queries holding connections:
   ```bash
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE state = 'active' ORDER BY duration DESC LIMIT 10;
   ```

## Remediation Steps
1. Terminate idle-in-transaction connections:
   ```bash
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE state = 'idle in transaction' AND state_change < now() - INTERVAL '5 minutes';
   ```
2. If triggered by a recent release with unclosed sessions, rollback the service:
   - Run deployment rollback to previous stable tag.
   - Gracefully restart service pods to drain leaked pool instances.
3. If legitimate traffic spike, increase pool size temporarily or scale database replicas.
