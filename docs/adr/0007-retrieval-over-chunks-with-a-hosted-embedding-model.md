---
status: accepted
---

# Retrieval over chunks, with a hosted embedding model

The assistant answered from a substring search. `search_articles_for_qa` took
the question's words, ran `title ILIKE '%word%' OR text ILIKE '%word%'`, and
handed the top eight articles to the model. This replaces that with hybrid
retrieval over passages.

## What the substring search could not do

It has no notion of meaning. "מה קורה עם יוקר המחיה?" does not retrieve a
paragraph reading "מחירי הדיור עלו ב-4%", because the two share no word — and
no threshold on word overlap ever could. Measured against the live corpus
before this change, that question returned three articles about the election.

ADR 0005 recorded the same finding for event grouping, on the same corpus:
4,602 of the article pairs a semantic reading joins share **zero** title tokens.
Retrieval sits on the same Hebrew.

Two smaller problems came with it. The unit was the whole article, so a
4,000-character piece was represented by whichever 300 characters `LEFT(text,
300)` returned; and the assistant was single-turn, so "ומה לגבי הארץ?" had
nothing to resolve against.

## Why this is a second vector space, not the one that exists

`articles.title_embedding` already holds a vector per article, from
`intfloat/multilingual-e5-small`. It cannot be reused here, for two independent
reasons.

**The API host cannot produce a query vector.** e5 runs through
sentence-transformers, which needs torch, which does not fit in Render's 512MB
free tier — CI asserts that `src.api.app` imports neither torch nor numpy. For
event clustering that constraint is survivable, because both sides of every
comparison are articles embedded during ingestion. Retrieval is not like that:
one side is a question typed a second ago. Something on the API host has to
embed it, and e5 never will on this plan.

**The granularity is wrong.** That vector covers the title plus 400 characters,
because its job is to decide whether two articles are the same event — and ADR
0005 measured the clustering threshold against exactly that string. Retrieval
wants the paragraph that answers the question, which is usually not in the first
400 characters. Re-cutting the passage to suit retrieval would silently
invalidate the event threshold.

So: `text-embedding-3-small` over HTTP, at 512 of its 1,536 Matryoshka
dimensions, in `article_chunks.embedding`. No local weights, so the same call
embeds a chunk on GitHub Actions and a question on Render. Two columns, two
models, two purposes; they are never compared.

The cost is small enough not to be the deciding factor: a few cents to embed
the corpus once, and a fraction of a cent per thousand questions. 512
dimensions rather than 1,536 is a third of the bytes an index scan moves out of
Neon, whose transfer quota this project has already exhausted once.

## Hybrid, because neither channel is enough

- **Vector alone** ranks chunks about a politician's camp above chunks that
  name him. Rare proper nouns are where dense retrieval is weakest, and Hebrew
  news is mostly proper nouns.
- **Lexical alone** is the search being replaced.

The two are fused with Reciprocal Rank Fusion (k=60), in SQL. Ranks rather than
scores: a cosine distance and a count of matched Hebrew substrings have no
common scale, and any direct weighting between them would be a number with no
defensible value. Fusing ranks needs no such number.

The lexical channel stays `ILIKE '%term%'` rather than becoming full-text
search. Postgres has no Hebrew stemmer, and `to_tsvector('simple', ...)` would
miss every prefixed form — "בכתבות" would not match "כתבות". A trigram GIN
index makes the unanchored match indexed rather than sequential, which is the
part that was missing before.

## What a question costs

One embedding request and one chat completion. Deliberately:

- **No planner call.** Both kinds of evidence are always fetched — the
  corpus-wide statistics and the retrieved passages — and the single answer
  call decides which it needs. Choosing between them in advance would cost a
  round trip to save two indexed queries. It also fixes the old assistant's most
  visible bug, where a question the statistics answered outright ("איזה נושא
  הכי מסוקר?") was refused because retrieval had found nothing relevant.
- **No query-rewrite call.** A follow-up prepends the previous user turn to form
  the search text. For a two-turn follow-up that is most of what a rewrite would
  have produced; over a longer drifting thread it is genuinely weaker, and the
  answer call still sees the history, so it can say so.
- **No tool-calling loop, no self-critique pass.** Each is another round trip on
  a host that sleeps when idle.

Small talk is answered before any of it — no embedding, no retrieval, no model.

## Consequences

- **A missing embedding key degrades rather than breaks.** The chunking pass
  needs no key, so chunks always exist and the lexical channel always works.
  The API reports `degraded: true` and the UI says so. Same
  fallback-rather-than-nothing choice as ADR 0005.
- **Citations are numbers the model must return, and are resolved, not
  trusted.** A number outside the range of passages shown is dropped, never
  clamped onto a real article — a fabricated citation must not become a
  plausible link.
- **At most two chunks per article reach an answer.** Without the cap, one long
  on-topic article contributes six near-identical passages and crowds out the
  second outlet's version of the story, which for this corpus is the worst
  available failure.
- **Conversation state lives in the client.** The API stays stateless; its host
  spins down when idle, and a session store would be the only part of it that
  had to survive that.
- **Changing the model, the dimension count, or the chunking invalidates every
  stored vector.** `article_chunks.embedding_model` is the gate that forces a
  re-embed, the same version-gate the event vectors and the polarization
  lexicon use.
