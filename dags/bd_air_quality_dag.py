"""Daily Airflow DAG: ingest -> dbt build (models + tests) -> refresh report.

Airflow runs in its own virtualenv; each task calls the project's tools through
the project virtualenv, so Airflow's dependency pins never clash with dbt's.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT = os.environ.get("BDAIR_HOME", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV_BIN = f"{PROJECT}/.venv/bin"
DBT = f"cd {PROJECT}/dbt && {VENV_BIN}/dbt"
DBT_FLAGS = "--profiles-dir ."

default_args = {
    "owner": "abed",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "retry_exponential_backoff": True,
}

with DAG(
    dag_id="bd_air_quality_daily",
    description="Bangladesh air-quality ELT: Open-Meteo -> Postgres -> dbt",
    schedule="0 3 * * *",  # 09:00 Asia/Dhaka
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["elt", "dbt", "air-quality"],
) as dag:
    ingest = BashOperator(
        task_id="ingest_incremental",
        bash_command=f"cd {PROJECT} && {VENV_BIN}/python -m bdair.pipeline incremental",
        env={"PYTHONPATH": f"{PROJECT}/src"},
        append_env=True,
    )
    source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"{DBT} source freshness {DBT_FLAGS}",
    )
    seed = BashOperator(task_id="dbt_seed", bash_command=f"{DBT} seed {DBT_FLAGS}")
    build = BashOperator(
        task_id="dbt_build",  # runs models and their tests in DAG order; a failed test stops downstream models
        bash_command=f"{DBT} build --exclude resource_type:seed {DBT_FLAGS}",
    )
    report = BashOperator(
        task_id="refresh_report",
        bash_command=f"cd {PROJECT} && {VENV_BIN}/python analysis/make_report.py",
        env={"PYTHONPATH": f"{PROJECT}/src"},
        append_env=True,
    )

    ingest >> source_freshness >> seed >> build >> report
