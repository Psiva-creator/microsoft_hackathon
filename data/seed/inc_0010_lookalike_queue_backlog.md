# Post-Mortem: notification-worker high latency due to 1M backlog in kafka-orders
## Summary
Incident affecting notification-worker, kafka-orders. Visible symptoms mirror memory_leak but root cause differs.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: notification-worker high latency due to 1M backlog in kafka-orders.
## Root Cause
Underlying root cause identified as queue_backlog: notification-worker high latency due to 1M backlog in kafka-orders.
## Resolution Steps
1. Confirmed symptoms are not due to memory_leak by inspecting logs.
2. Applied remediation for queue_backlog.
3. Restored service availability.
