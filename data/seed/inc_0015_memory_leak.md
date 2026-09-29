# Post-Mortem: Incident INC-0015
## Summary
Service outage affecting checkout-api for 58 minutes.
## Symptoms
- container OOMKilled
- JVM GC pause times > 10s
- Error logs: java.lang.OutOfMemoryError: Java heap space at com.acme.worker.TaskProcessor.run(TaskProcessor.java:184)
## Root Cause
Identified issue in memory_leak affecting subsystem stability: container OOMKilled.
## Resolution Steps
1. Followed runbook RB-memory-leak-restart.
2. Investigated logs from checkout-api and applied fix.
3. Validated health check.
