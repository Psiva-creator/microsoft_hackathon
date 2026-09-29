# Post-Mortem: Incident INC-0051
## Summary
Service outage affecting notification-worker, kafka-orders for 48 minutes.
## Symptoms
- CrashLoopBackOff on service pods
- syntax error on startup
- Error logs: FATAL: invalid configuration parameter 'max_connections_limit' in config.yaml
## Root Cause
Identified issue in bad_deploy affecting subsystem stability: CrashLoopBackOff on service pods.
## Resolution Steps
1. Followed runbook RB-bad-deploy-rollback.
2. Investigated logs from notification-worker and applied fix.
3. Validated health check.
