# 📁 Project Directory Structure

---

## Table of Contents

- [Overview](#overview)
- [Directory Tree](#directory-tree)

---

## Overview

This document shows the complete folder and file structure of the news-pipeline project.

---

## Directory Tree

```
news-pipeline/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── contracts/
│   │   ├── schemas.md
│   │   ├── ids_and_versioning.md
│   │   └── dq_rules.md
│   └── diagrams/
│       ├── dataflow.mmd
│       └── folder_layout.mmd
├── airflow/
│   ├── dags/
│   │   ├── crawl_latest_to_gcs.py
│   │   └── daily_snapshot_process_to_bq.py
│   └── config/
│       └── variables.example.json
├── src/
│   ├── common/
│   │   ├── canonical_url.py
│   │   ├── hashing.py
│   │   ├── time_utils.py
│   │   └── logging.py
│   ├── crawling/
│   │   ├── sources/
│   │   │   ├── haaretz.py
│   │   │   ├── ynet.py
│   │   │   ├── mako.py
│   │   │   ├── news12.py
│   │   │   ├── reshet13.py
│   │   │   └── channel14.py
│   │   ├── extract_article.py
│   │   └── extract_comments.py
│   ├── nlp/
│   │   ├── normalize.py
│   │   ├── sentence_splitter.py
│   │   └── tokenize.py
│   ├── lexicon/
│   │   ├── build_expanded_lexicon.py
│   │   ├── load_lexicon.py
│   │   └── word2category.py
│   ├── features/
│   │   ├── article_windows.py
│   │   ├── comments_scoring.py
│   │   └── aggregates.py
│   ├── io/
│   │   ├── gcs_reader.py
│   │   ├── gcs_writer.py
│   │   ├── parquet_writer.py
│   │   └── bq_loader.py
│   └── dq/
│       ├── validate_windows.py
│       ├── validate_comments.py
│       └── validate_aggregates.py
├── data/
│   ├── lexicon_base/
│   │   ├── category1.txt
│   │   ├── ...
│   │   └── category7.txt
│   ├── lexicon_expanded/
│   │   ├── lexicon_expanded.json
│   │   └── lexicon_version.txt
│   ├── comment_lexicon_base/
│   │   └── polar_words.txt
│   └── comment_lexicon_expanded/
│       ├── comment_lexicon_expanded.json
│       └── comment_lexicon_version.txt
└── sql/
    ├── bq/
    │   ├── create_tables.sql
    │   ├── merge_articles.sql
    │   ├── merge_windows_features.sql
    │   ├── merge_comments_features.sql
    │   └── merge_article_comments_agg.sql
    └── staging/
        ├── create_staging_tables.sql
        └── truncate_staging.sql
```