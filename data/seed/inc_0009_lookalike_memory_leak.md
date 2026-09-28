# Post-Mortem: notification-worker OOMKilled after processing large attachment
## Summary
Incident affecting notification-worker, kafka-orders. Users observed severe latency and 500 errors.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: notification-worker OOMKilled after processing large attachment.
## Root Cause
Underlying root cause identified as memory_leak: notification-worker OOMKilled after processing large attachment.
## Resolution Steps
1. Identified root cause in system metrics.
2. Applied recovery steps according to standard runbook.
3. System returned to normal operating capacity.
