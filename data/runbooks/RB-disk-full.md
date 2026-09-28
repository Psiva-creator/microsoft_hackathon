---
id: RB-disk-full
title: Disk Space Exhaustion on Critical Node
services: [postgres-primary, kafka-orders, redis-cache]
---

# RB-disk-full: Disk Space Exhaustion on Critical Node

## Symptoms
- Alert: `DiskSpaceExhaustionCritical` (>95% root or data partition used).
- Database or message broker fails to write WAL logs: `No space left on device`.
- Services crash or enter read-only mode abruptly.

## Verification Steps
1. Identify the filesystem and directories consuming space:
   ```bash
   df -h
   du -sh /var/log/* /data/* | sort -hr | head -n 10
   ```
2. Check if unrotated application logs or core dumps filled the disk:
   ```bash
   ls -lh /var/log/*.gz /tmp/core.*
   ```

## Remediation Steps
1. Safely remove archived log files older than 7 days:
   ```bash
   find /var/log/ -name "*.log.*.gz" -mtime +7 -delete
   ```
2. Truncate orphaned temporary files in `/tmp`:
   ```bash
   rm -rf /tmp/*-cache*
   ```
3. For Postgres WAL bloat, verify replication slots are not blocking archive removal:
   ```bash
   SELECT slot_name, active, pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) FROM pg_replication_slots;
   ```
4. Expand underlying persistent volume (EBS/PVC) if storage needs permanent upgrade.
