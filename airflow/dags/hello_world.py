from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def print_hello():
    print('Hello world!')
    return "success"

with DAG(
    dag_id='hello_world_dag',
    start_date=datetime(2023, 1, 1),
    schedule=None,
    catchup=False,
    tags=['my_first_dag']
) as dag:

    hello_task = PythonOperator(
        task_id='hello_task',
        python_callable=print_hello
    ) 

    hello_task