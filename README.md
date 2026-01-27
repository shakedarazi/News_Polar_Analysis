# News_Polar_Analysis



flowchart TD
  A[News Crawlers / Ingest] --> B[STAGING: raw JSON<br/>article_json + comments_json[]<br/>Keys: article_id, comment_id]

  %% P-FLOW
  B -->|title+lead+body + article_id| P1[P-FLOW: LLM Annotator<br/>P-score contract v1]
  P1 --> P2[Write SILVER: silver_articles_p<br/>PK: article_id<br/>Fields: p_components_json, evidence, p_version, input_hash, run_id]

  %% A-FLOW with Lemma
  B -->|comments_json[] -> rows| A0[A0: Lemmatization Job/Service<br/>Input: comment_text<br/>Output: lemmas[] + lemma_version]
  A0 --> A0S[Write SILVER: silver_comments_lemmas<br/>PK: comment_id<br/>FK: article_id<br/>Fields: lemmas[], lemma_version, run_id]

  A0 --> A1[A1: Shimhon Lexicon Match<br/>on lemmas[] + lexicon_lemmas]
  A1 --> A1S[Write SILVER: silver_comments_a_scored<br/>PK: comment_id<br/>FK: article_id<br/>Fields: a_score, matched_terms?, lexicon_version, lemma_version, run_id]

  A1S --> A2[A2: BigQuery Aggregation per article]
  A2 --> A2S[Write SILVER: silver_articles_a_agg<br/>PK: article_id<br/>Fields: a_mean/a_tail/a_var/num_comments<br/>lexicon_version, lemma_version, run_id]

  %% GOLD
  P2 --> G[Build GOLD / MART (BI-ready)<br/>JOIN on article_id (+ run_id optional)]
  A2S --> G

  G --> BI[BI Dashboard<br/>P vs A, Gap, Outlet×Category, Author rankings]
