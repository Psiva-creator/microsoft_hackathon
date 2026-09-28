---
id: RB-memory-leak-restart
title: Memory Leak Mitigation and Pod Restart
services: [checkout-api, orders-service, notification-worker]
---

# RB-memory-leak-restart: Memory Leak Mitigation and Pod Restart

## Symptoms
- Continual rise in RSS memory consumption over time without plateau.
- Frequent container terminations with exit code 137 (`OOMKilled`).
- Garbage collection pauses causing latency spikes.

## Verification Steps
1. Review memory utilization trends in Prometheus:
   ```promql
   container_memory_working_set_bytes{container="<service>"}
   ```
2. Check termination reason on recently restarted pods:
   ```bash
   kubectl get pods -l app=<service> -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[*].lastState.terminated.reason}{"\n"}{end}'
   ```
3. Take heap dump before restarting if debugger profiling is enabled:
   ```bash
   jcmd 1 GC.heap_dump /tmp/heap.hprof
   ```

## Remediation Steps
1. Perform rolling restart of the deployment to recover immediate memory capacity:
   ```bash
   kubectl rollout restart deployment/<service>
   ```
2. If leak rate is severe, temporarily bump container memory limits by 50%:
   ```bash
   kubectl set resources deployment/<service> --limits=memory=2Gi
   ```
3. File high-priority ticket with heap analysis attached for developer investigation.
