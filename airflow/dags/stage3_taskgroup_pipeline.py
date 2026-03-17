from datetime import datetime
import logging
import time

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

logger = logging.getLogger("airflow.task")


def _group_step(step_name: str, delay_sec: int = 2):
    logger.info(f"[task_group] start: {step_name}")
    time.sleep(delay_sec)
    logger.info(f"[task_group] done: {step_name}")


with DAG(
    dag_id="stage3_taskgroup_pipeline",
    start_date=datetime(2026, 3, 17),
    schedule=None,
    catchup=False,
    tags=["stage_3", "task_group"],
) as dag:
    start = EmptyOperator(task_id="start")

    with TaskGroup(group_id="etl_group") as etl_group:
        extract = PythonOperator(
            task_id="extract",
            python_callable=_group_step,
            op_kwargs={"step_name": "extract", "delay_sec": 2},
        )

        transform = PythonOperator(
            task_id="transform",
            python_callable=_group_step,
            op_kwargs={"step_name": "transform", "delay_sec": 3},
        )

        load = PythonOperator(
            task_id="load",
            python_callable=_group_step,
            op_kwargs={"step_name": "load", "delay_sec": 2},
        )

        extract >> transform >> load

    finish = EmptyOperator(task_id="finish")

    start >> etl_group >> finish
