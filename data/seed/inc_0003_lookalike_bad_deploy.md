# Post-Mortem: INC-0003 - payments-gateway crash on startup after missing config env var
## Summary
Incident INC-0003 affecting payments-gateway.
## Symptoms
- CrashLoopBackOff on service pods
- syntax error on startup
- Logs: FATAL: invalid configuration parameter 'max_connections_limit' in config.yaml
## Root Cause
Root cause identified as bad_deploy: payments-gateway crash on startup after missing config env var.
## Resolution Steps
1. Consulted runbook RB-bad-deploy-rollback.
2. Restarted impacted pods in payments-gateway.
