docs/ — Project Documentation (Source of Truth)

This folder is the single source of truth for the project’s design, contracts, and decisions.

Rule:
Code, Airflow DAGs, and SQL must be derived from the documents in this folder — never the other way around.

Any change that affects determinism, schemas, IDs, algorithms, or metrics must be documented here first.

Folder Structure

docs/

README.md

architecture/

overview.md

dataflow.md

concurrency.md

contracts/

entities.md

ids_and_keys.md

versioning.md

data_quality.md

pipelines/

ingestion_dag.md

processing_dag.md

staging_and_merge.md

algorithms/

article_windows.md

comments_scoring.md

aggregation.md

schemas/

gcs_raw.md

gcs_snapshot.md

staging_parquet.md

bigquery_tables.md

lexicon/

lexicon_strategy.md

expansion_rules.md

diagrams/

dataflow.mmd

gcs_layout.mmd

staging_to_bq.mmd

concurrency.mmd

What Each Section Is Responsible For

architecture/
Explains system-level design decisions:

Why the pipeline is batch-oriented and not streaming

Why the system uses two DAGs

Why article text and audience comments are separated

Deterministic constraints at the architectural level

contracts/
Defines the hard contract of the system:

Core entities and their meaning (Article, Window, Comment)

Identification and primary keys

Versioning rules

Data Quality rules

Any change here may break reproducibility and downstream analysis.

pipelines/
Defines the operational behavior:

DAG 1 (Ingestion): what it does and what it does not do

DAG 2 (Snapshot + Processing): lifecycle and responsibilities

Staging to BigQuery load and MERGE semantics

algorithms/
Defines the exact algorithms used by the system:

Article window segmentation and feature extraction

Comment scoring and like-weight logic

Aggregation logic (weighted mean and weighted p85)

schemas/
Defines the field-level structure of data:

Raw JSON stored in GCS

Snapshot JSON with comments

Staging Parquet schemas

Final BigQuery tables and keys

lexicon/
Defines the lexicon strategy:

Baseline approach: Expanded Lexicon (Approach A)

Offline expansion rules and constraints

Future option: Prefix stripping (Approach B), not enabled

diagrams/
Contains Mermaid diagram files that visualize:

End-to-end dataflow

GCS folder layout

Staging to BigQuery and MERGE

Concurrency model

Authoritative Order of Work

Update documentation in docs/

Implement application code

Implement Airflow DAGs

Implement BigQuery SQL

Validate outputs against Data Quality rules

Determinism and Reproducibility Requirements

The system must guarantee:

Same input produces the same output

No non-deterministic behavior in the critical path

Every output record is tagged with:

pipeline_version

lexicon_version

comment_lexicon_version

run_id

Next Documents to Create

architecture/overview.md

architecture/dataflow.md

architecture/concurrency.md

contracts/entities.md

contracts/ids_and_keys.md

contracts/versioning.md

contracts/data_quality.md