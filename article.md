# My Hand-Built Agent Memory Lost to Keyword Search. Enter Hindsight.

I spent weeks building a brain-inspired memory system for an on-call incident agent, then ran a benchmark and watched it lose to a keyword search that scores token overlap. Recall@3 was 63.3% for my hybrid retriever and 78.3% for the keyword baseline.

This is a post about that result, what I think caused it, and why it sent me looking at [Hindsight](https://github.com/vectorize-io/hindsight), an open-source agent memory system, for the part of the stack I had the least business hand-rolling.

## What the agent does

When production breaks at 3 AM, the useful knowledge is buried in old Slack threads and closed tickets. The agent takes an alert, recalls similar past incidents, investigates the live system with read-only tools, and proposes a cause with cited precedents. I organized the memory around the human brain, mostly as a way to keep the design honest:

- **Working memory** is Redis. It holds the live incident: events, services touched, current hypotheses. When an incident resolves, every key gets a 72-hour TTL.
- **Episodic memory** is PostgreSQL 16 with pgvector. Each past incident is stored with two embeddings, one built from symptoms only (`emb_symptom`) for matching a live cue, and one built from symptoms plus root cause and resolution (`emb_full`) for clustering.
- **Semantic memory** is the runbook store and a service dependency graph.
- **Procedural memory** is a Laplace-smoothed success probability per runbook, updated from engineer feedback.
- **Consolidation** is a nightly job that clusters incidents into patterns with agglomerative clustering.

Redis gets the cheap, volatile stuff:

```python
# app/memory/working.py
DEFAULT_TTL_SECONDS = 72 * 3600  # 72 hours (259,200 seconds)
MAX_CONTEXT_EVENTS = 30
ACTIVE_STATUSES = {"open", "investigating", "postmortem_draft"}
TERMINAL_STATUSES = {"resolved", "confirmed", "archived"}
```

That part worked and I would not change it. Live incident state is a cache with a lifecycle, and Redis is the right tool. The trouble started in episodic recall.

## The look-alike problem

The thing that makes incident memory hard is that outages *look* alike. Two different failures can produce the same `checkout-api` latency spike and the same HTTP 503s. A plain vector search sees two similar incidents and picks the closest one.

My seed corpus has 64 incidents, and several are deliberate look-alike pairs. `INC-0007` is database connection pool exhaustion. `INC-0019` is a CoreDNS pod eviction. Both present as timeouts on the same service. In the DNS scenario the log line that matters is `dial tcp: lookup postgres-primary: no such host`, which a pool-exhaustion story cannot explain.

So retrieval fuses five signals, each with a hand-set weight:

```python
# app/config.py
W_VEC:  float = Field(default=0.35)
W_FTS:  float = Field(default=0.15)
W_FP:   float = Field(default=0.20)
W_SVC:  float = Field(default=0.15)
W_CODE: float = Field(default=0.15)
```

```python
# app/memory/retrieval.py
base = (
    w_vec * v      # embedding cosine similarity
    + w_fts * f    # keyword token overlap
    + w_fp * fp    # stack/message fingerprint match
    + w_svc * s    # service overlap, a gentle prior
    + w_code * c   # touched files match
)
final = base * float(inc["weight"]) * (0.85 + 0.30 * best_rb_p)
```

The last line scales the score by an incident's decay weight and by how often its runbook actually worked. The fingerprint term is the one I was proudest of. It hashes the exception type plus the innermost three *application* frames, ignoring framework frames, so the same bug hashes the same way across two incidents:

```python
# app/core/fingerprint.py
innermost = app_frames[-3:]  # innermost 3 application frames
formatted_frames = [f"{f.file}:{f.function}" for f in innermost]
raw_stack_fp = f"{exc_type}|" + "|".join(formatted_frames)
stack_fp = hashlib.sha1(raw_stack_fp.encode("utf-8")).hexdigest()[:16]
```

Retrieval also does something vectors cannot: it flags mismatches. If the cue's trigger type is a deploy and the precedent's is not, the result carries `trigger_mismatch`. If services do not overlap, it carries `service_mismatch`. The reasoning layer treats those flags as evidence against the precedent, and confidence is deterministically capped at `low` when strong mismatches are present. When nothing matches at all, the agent says `precedent_strength: "none"` instead of forcing an analogy.

## The benchmark

I built a leave-one-out evaluation: 60 cases, each cue drawn from an incident, with that incident excluded from the search so the engine has to find related precedents. I ran the full hybrid against the two single-signal baselines and dropped one signal at a time. This is on a 64-incident seeded corpus, so treat every number as a small-sample result.

| Mode | Recall@1 | Recall@3 | Recall@5 | MRR |
| :--- | :---: | :---: | :---: | :---: |
| Keyword only | 60.0% | 78.3% | 86.7% | 0.706 |
| Vector only | 46.7% | 61.7% | 75.0% | 0.568 |
| Full hybrid | 55.0% | 63.3% | 70.0% | 0.601 |
| Hybrid without vector | 48.3% | 63.3% | 76.7% | 0.584 |
| Hybrid without keyword | 45.0% | 58.3% | 70.0% | 0.535 |
| Hybrid without fingerprints | 46.7% | 60.0% | 68.3% | 0.543 |
| Hybrid without service graph | 61.7% | 71.7% | 76.7% | 0.678 |

Two rows are uncomfortable.

The full hybrid barely beats vector-only on Recall@3 and loses clearly to the keyword baseline. And dropping the service graph *raised* Recall@3 from 63.3% to 71.7%. A signal I had added to help was hurting.

What the table does support: fingerprints earn their place. Removing them lowers Recall@3 and Recall@5, and the misses I read through were mostly look-alike confusions. Removing the keyword signal hurts the most, which says something about incident text. Error strings, service names, and exit codes are exact tokens, and exact tokens are what keyword search is good at.

## What I think went wrong

I do not have a controlled experiment for this, so this is diagnosis, not proof.

**A linear blend of hand-set weights is a fragile fusion method.** The five scores live on different scales. Cosine similarity clusters in a narrow band, token overlap is a fraction of twelve, and fingerprints are effectively 0, 0.8, or 1. Multiplying them by weights I picked by feel, then summing, lets whichever signal has the widest spread dominate. A weak signal with a wide range can outvote a strong one with a narrow range. The service prior is the clearest case. It adds a flat 0.3 whenever any service overlaps, which pushes same-service incidents up regardless of whether the failure mode matches.

**I tuned by intuition against a tiny corpus.** With 60 cases, one changed ranking moves Recall@1 by 1.7 points. I could not have tuned five weights reliably even if I had tried.

**I was rebuilding retrieval infrastructure instead of building the agent.** Rank fusion and reranking are known problems with known solutions, and I was solving them badly with a `sum()`.

## Where Hindsight fits

This is the part I did not know when I started. [Hindsight's documentation](https://hindsight.vectorize.io/) describes recall as running four strategies in parallel (semantic vectors, BM25 keyword matching, graph traversal over entities and their links, and temporal filtering), then merging results with reciprocal rank fusion and a cross-encoder reranker. Reciprocal rank fusion sidesteps my scale problem because it combines *ranks*, not raw scores. A cosine of 0.91 and a fingerprint of 1.0 never have to be compared to each other.

Hindsight's three operations also line up with my hand-built layers more closely than I expected:

| My layer | Hindsight operation |
| :--- | :--- |
| Post-mortem writeback into episodic memory | `retain` |
| The recall engine and its weighted fusion | `recall` |
| Nightly consolidation into patterns | `reflect` |

On the retain side, the project describes turning stored content into entities, relationships, and time series alongside vector and keyword indexes. That is the service dependency graph I built by hand, except derived from the text I feed it. Its API is small:

```python
from hindsight_client import Hindsight

client = Hindsight(base_url="http://localhost:8888")

client.retain(bank_id="incidents", content=postmortem_text)
client.recall(bank_id="incidents", query="checkout-api 503, no such host")
client.reflect(bank_id="incidents", query="What usually causes checkout timeouts?")
```

I want to be precise about what this changes, because the benchmark taught me to be. Swapping the recall engine does not remove the need for my fingerprints or my mismatch flags. Those encode incident-specific knowledge about what makes two stack traces the same bug, and that logic should stay in my code, applied to whatever Hindsight returns. What should go is my fusion arithmetic, my consolidation job, and the maintenance burden of both. The evaluation harness stays too. It is now the thing that tells me whether the swap helps, on the same 60 cases, with the same leave-one-out rule.

I have not yet run that comparison, so I am not going to tell you it wins. The experiment is queued.

## Guardrails that survived

Retrieval was the weak part, but the safety design held up under every scenario I ran, and I would keep all of it.

The tool registry is read-only, enforced by `ALLOW_ACTIONS=false`. Rollbacks, restarts, and config changes are never executed. They appear under `needs_human_decision` for a person to approve. A redaction pass scrubs AWS keys, GitHub and Slack tokens, JWTs, and bearer credentials before any text reaches the model or storage. Cited incident IDs are checked against the database, and an ID that does not resolve is moved to `dropped_citations` and lowers confidence. An agent that invents a precedent at 3 AM is worse than no agent.

There is also a `pr-check` command that inverts the memory: given the files in a pull request, it looks up past incidents linked to those files and warns when a change touches code that has caused an outage before.

## Lessons

**1. Benchmark before you believe your architecture.** My design felt right for weeks. Sixty test cases took an afternoon and disproved a large part of it.

**2. Ablations are worth more than headline numbers.** The single-signal baselines told me the hybrid was not winning. The leave-one-out ablations told me *which* signal was hurting.

**3. Exact tokens matter in operational text.** Error strings, hostnames, and exit codes are lexical. Do not let embeddings replace keyword search.

**4. Fuse ranks, not scores.** Adding numbers from different distributions with hand-picked weights is a bug that looks like a design.

**5. Keep your domain logic and rent your plumbing.** Fingerprints and mismatch flags are mine. General-purpose retrieval, fusion, and consolidation are a solved problem that [agent memory tooling](https://vectorize.io/what-is-agent-memory) exists to handle, and I would rather spend my time on the first kind.

The code, seed corpus, and evaluation harness are all in the repository. If you run the harness against your own retriever, I would like to see where it lands.
