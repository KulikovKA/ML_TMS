from datetime import datetime
import logging

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

logger = logging.getLogger("airflow.task")


with DAG(
    dag_id="stage3_subdag_style_parent",
    start_date=datetime(2026, 3, 17),
    schedule=None,
    catchup=False,
    tags=["stage_3", "subdag_style"],
) as dag:
    start = EmptyOperator(task_id="start")

    trigger_child = TriggerDagRunOperator(
        task_id="run_child_pipeline",
        trigger_dag_id="stage3_subdag_child",
        wait_for_completion=True,
        poke_interval=5,
        allowed_states=["success"],
        failed_states=["failed"],
        reset_dag_run=True,
    )

    finish = EmptyOperator(task_id="finish")

    start >> trigger_child >> finish
