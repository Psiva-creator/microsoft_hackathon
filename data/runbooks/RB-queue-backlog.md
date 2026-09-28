---
id: RB-queue-backlog
title: Message Queue Backlog and Worker Lag Relief
services: [kafka-orders, notification-worker, orders-service]
---

# RB-queue-backlog: Message Queue Backlog and Worker Lag Relief

## Symptoms
- Consumer lag on Kafka topics grows continuously.
- Customer notifications or downstream order processing delayed by minutes or hours.
- Poison-pill message blocking consumer partition processing.

## Verification Steps
1. Inspect Kafka consumer group lag:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server kafka-orders:9092 --describe --group order-processors
   ```
2. Check worker logs for parsing errors or deadlocks on specific messages:
   ```bash
   kubectl logs -l app=notification-worker --tail=100 | grep -E "ERROR|poison"
   ```
3. Verify worker pod CPU and concurrency utilization.

## Remediation Steps
1. Scale out consumer worker replicas up to partition count limit:
   ```bash
   kubectl scale deployment/notification-worker --replicas=10
   ```
2. If blocked by an unparseable malformed payload (poison pill):
   - Route failed offsets directly to the Dead Letter Queue (DLQ).
   - Reset consumer offset to skip the blocking message:
     ```bash
     kafka-consumer-groups.sh --bootstrap-server kafka-orders:9092 --group order-processors --reset-offsets --shift-by 1 --execute --topic orders.incoming
     ```
3. Verify lag metric decreases at a steady rate.
