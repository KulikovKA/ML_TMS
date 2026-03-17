from datetime import datetime
import logging
import time

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger("airflow.task")


def _child_step(step_name: str, delay_sec: int = 2):
    logger.info(f"[child] start: {step_name}")
    time.sleep(delay_sec)
    logger.info(f"[child] done: {step_name}")


with DAG(
    dag_id="stage3_subdag_child",
    start_date=datetime(2026, 3, 17),
    schedule=None,
    catchup=False,
    tags=["stage_3", "subdag_style"],
) as dag:
    child_extract = PythonOperator(
        task_id="child_extract",
        python_callable=_child_step,
        op_kwargs={"step_name": "extract", "delay_sec": 2},
    )

    child_transform = PythonOperator(
        task_id="child_transform",
        python_callable=_child_step,
        op_kwargs={"step_name": "transform", "delay_sec": 3},
    )

    child_load = PythonOperator(
        task_id="child_load",
        python_callable=_child_step,
        op_kwargs={"step_name": "load", "delay_sec": 2},
    )

    child_extract >> child_transform >> child_load
