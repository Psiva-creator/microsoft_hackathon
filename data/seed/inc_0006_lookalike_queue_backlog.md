# Post-Mortem: INC-0006 - notification-worker high latency due to 1M backlog in kafka-orders
## Summary
Incident INC-0006 affecting notification-worker, kafka-orders.
## Symptoms
- Kafka consumer lag exceeding 500k messages
- event ingestion delay
- Logs: CommitFailedException: Commit cannot be completed since the group has already rebalanced
## Root Cause
Root cause identified as queue_backlog: notification-worker high latency due to 1M backlog in kafka-orders.
## Resolution Steps
1. Consulted runbook RB-queue-backlog.
2. Restarted impacted pods in notification-worker.
