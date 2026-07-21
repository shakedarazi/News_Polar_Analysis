"""
DAG 1 — Ingestion: discover and freeze new articles every 6 hours.

Schedule: 0 */6 * * *  (00:00, 06:00, 12:00, 18:00 UTC)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "/opt/news-polar"
RUN_SCRIPT = f"{PROJECT_ROOT}/scripts/run_ingestion.sh"

default_args = {
    "owner": "news-polar",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="crawl_latest_to_gcs",
    default_args=default_args,
    description="Discover articles from all sources and freeze raw snapshots",
    schedule_interval="0 */6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ingestion"],
) as dag:
    crawl_all = BashOperator(
        task_id="crawl_all_sources",
        bash_command=f"{RUN_SCRIPT}",
    )
