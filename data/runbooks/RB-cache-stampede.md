---
id: RB-cache-stampede
title: Cache Stampede and Redis Key Expiry Stabilization
services: [redis-cache, inventory-service, checkout-api]
---

# RB-cache-stampede: Cache Stampede and Redis Key Expiry Stabilization

## Symptoms
- Redis cache hit ratio drops sharply (e.g. from >95% to <50%).
- Downstream database CPU spikes to near 100% due to un-cached queries.
- Mass synchronized key expiry following bulk data refreshes.

## Verification Steps
1. Inspect Redis hit ratio and operations per second:
   ```bash
   redis-cli info stats | grep -E "keyspace_hits|keyspace_misses"
   ```
2. Identify hot keys or sudden key expirations:
   ```bash
   redis-cli --hotkeys
   ```
3. Check database active query volume for identical read queries.

## Remediation Steps
1. Enable probabilistic early expiration or single-flight request coalescing in application tier.
2. Introduce randomized TTL jitter (+/- 15% delta) on bulk write caches to prevent synchronized expiry:
   ```python
   ttl = base_ttl + random.randint(-60, 60)
   ```
3. Pre-warm high-frequency inventory cache keys using background cache filler script:
   ```bash
   python scripts/warm_cache.py --service inventory
   ```
4. Confirm Redis cache hit ratio returns above 90% and database CPU normalizes.
