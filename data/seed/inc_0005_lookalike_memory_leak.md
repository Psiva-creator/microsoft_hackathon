# Post-Mortem: INC-0005 - notification-worker OOMKilled after processing large attachment
## Summary
Incident INC-0005 affecting notification-worker, kafka-orders.
## Symptoms
- container OOMKilled
- JVM GC pause times > 10s
- Logs: Kubelet: container exceeded memory limit of 2Gi and was killed (OOMKilled)
## Root Cause
Root cause identified as memory_leak: notification-worker OOMKilled after processing large attachment.
## Resolution Steps
1. Consulted runbook RB-memory-leak-restart.
2. Restarted impacted pods in notification-worker.
