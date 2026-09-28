# Post-Mortem: INC-0024 - Synchronized Cache Expiry Causing Database Overload

## Executive Summary
On 2026-04-11 at 00:05 UTC, inventory-service database CPU surged to 95% following a sharp drop in redis-cache hit ratio from 96% to 41%. Service degradation lasted 52 minutes.

## Symptoms
- redis-cache hit ratio dropped abruptly.
- Postgres primary CPU pinned at 98%.
- Inventory queries timing out with 504 Gateway Timeout.

## Root Cause
A nightly bulk data refresh in services/inventory/cache.py set identical 24-hour TTLs across 800,000 product inventory keys, causing synchronized mass expiry at midnight.

## Resolution Steps
1. Executed runbook RB-cache-stampede.
2. Ran temporary cache pre-warming script to re-populate hot product keys.
3. Deployed patch introducing randomized TTL jitter (+/- 15 minutes) to avoid synchronized expiration.
