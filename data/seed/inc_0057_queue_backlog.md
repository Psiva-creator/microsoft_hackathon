# Post-Mortem: Incident INC-0057
## Summary
Service outage affecting payments-gateway, auth-service, checkout-api for 55 minutes.
## Symptoms
- Kafka consumer lag exceeding 500k messages
- event ingestion delay
- Error logs: CommitFailedException: Commit cannot be completed since the group has already rebalanced
## Root Cause
Identified issue in queue_backlog affecting subsystem stability: Kafka consumer lag exceeding 500k messages.
## Resolution Steps
1. Followed runbook RB-queue-backlog.
2. Investigated logs from payments-gateway and applied fix.
3. Validated health check.
