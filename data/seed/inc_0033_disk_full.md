# Post-Mortem: Incident INC-0033
## Summary
Service outage affecting checkout-api for 39 minutes.
## Symptoms
- database write rejections
- disk capacity at 100%
- Error logs: PANIC: could not write to log file: No space left on device
## Root Cause
Identified issue in disk_full affecting subsystem stability: database write rejections.
## Resolution Steps
1. Followed runbook RB-disk-full.
2. Investigated logs from checkout-api and applied fix.
3. Validated health check.
