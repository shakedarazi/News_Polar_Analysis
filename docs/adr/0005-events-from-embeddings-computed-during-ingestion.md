---
status: accepted
---

# Events from embeddings, computed during ingestion

Event detection grouped articles by how many title words they shared. In Hebrew
that finds a minority of what it should, and the module said so: its own
docstring called itself "the simplest thing that could plausibly work" and named
`get_events()` as the seam to replace it through. This records the replacement.

## Why the lexical grouping had to go

Two outlets covering one story rarely reuse each other's words. Each desk writes
its own headline, and Hebrew morphology fuses prefixes onto the words that would
otherwise have matched, so a token-overlap test sees two unrelated articles.

Measured on 1,436 categorised articles:

| | events | covered by 2+ outlets | articles in an event |
|---|---|---|---|
| lexical (Jaccard ≥ 0.34 on titles) | 69 | 32 | 156 |
| semantic (cosine ≥ 0.93) | 145 | 69 | 328 |

Of the 107 article pairs the lexical grouping joins, the semantic one keeps 70
and adds 81 more. 4,602 of the pairs a semantic reading brings together share
**zero** title tokens, so no threshold on word overlap could ever have found
them.

## The threshold belongs to the text, not to the model

`CLUSTER_SIMILARITY_THRESHOLD = 0.93` was measured on this corpus by reading
clusters at each step, and it is only valid for what is currently embedded:
`"{title}. {first 400 characters of body}"`.

Embedding **titles alone** breaks it, and not subtly. Unrelated Hebrew headlines
then sit at a median cosine of 0.859, 1% of all pairs clear 0.90, and clusters
become topic blobs — three separate stabbings in three towns read as one event.
A headline says what kind of thing happened; the lead says which one.

Articles with under 400 characters of extracted body are 36% of the corpus and
are deliberately **not** excluded: at this threshold they cluster at 22.0%
against 23.3% for articles with a full lead, so they are not shut out.

## Greedy assignment, not connected components

The lexical grouping used union-find, which joins A to C whenever some B is
close to both. At a high threshold that still chains whole storylines together.
Greedy seeding gives each article one chance to join the first cluster that
claims it. This is pinned by test; it is the property that makes the measured
threshold mean anything, and the threshold does not transfer to connected
components.

The cost is real and accepted: an article already claimed by one event cannot
join a better one later. That is why the sweep was read by hand rather than
scored, and why 0.93 sits in the middle of the clean band rather than at its
edge.

## Where it runs

Embedding needs torch. The API does not have it and must not:

- **GitHub Actions** (7GB) installs `requirements-embed.txt`, embeds new
  articles, reclusters the whole corpus, writes `articles.event_id`.
- **Render** (512MB free tier) installs only `requirements.txt` and reads that
  column.

Clustering runs there rather than on read for a second reason. Doing it on read
would pull 1,436 × 384 floats out of Neon on every cache miss, and
`event_grouping`'s cache exists precisely because re-reading the corpus on every
`/api/alerts` poll had already exhausted the project's data transfer quota.

Reclustering is whole-corpus, not incremental — an 8MB similarity matrix and
under a second — which avoids deciding what happens when a new article should
have merged two events that already exist.

## Consequences

- **The lexical grouping stays, as a fallback.** On a database where no
  embedding pass has run, showing the events it can find beats showing none.
- **The choice is per corpus, never per article.** A response never mixes the
  two definitions of "event", for the same reason the system has only one notion
  of article identity.
- **Event ids are derived, not allocated.** The id is the seed article's id, so
  the same corpus reclusters to the same ids and a link survives a recluster as
  long as the seed still leads its event.
- **`event_id` is not the article dedup key.** `article_id = sha256(canonical_url)`
  remains the only identity; `event_id` is a grouping that recomputes and can
  change.
- **Changing the model or `PASSAGE_LEAD_CHARS` voids the threshold.** Re-measure
  before shipping either.
