# Post-Mortem: Incident INC-0045
## Summary
Service outage affecting payments-gateway, orders-service for 50 minutes.
## Symptoms
- container OOMKilled
- JVM GC pause times > 10s
- Error logs: java.lang.OutOfMemoryError: Java heap space at com.acme.worker.TaskProcessor.run(TaskProcessor.java:184)
## Root Cause
Identified issue in memory_leak affecting subsystem stability: container OOMKilled.
## Resolution Steps
1. Followed runbook RB-memory-leak-restart.
2. Investigated logs from payments-gateway and applied fix.
3. Validated health check.
