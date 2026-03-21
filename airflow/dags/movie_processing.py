from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import time
import pandas as pd
from sqlalchemy import create_engine
import logging

logger = logging.getLogger("airflow.task")

# URL берем из окружения, чтобы DAG работал в обоих вариантах запуска Compose.
DB_URL = os.getenv("MOVIES_DB_URL", "postgresql://postgres:admin@db:5432/movies_db")


TEMP_FILE = '/opt/airflow/logs/temp_stats.csv'

def extract_and_transform():
    engine = create_engine(DB_URL)
    total_rows = 0
    chunk_size = int(os.getenv("MOVIES_ETL_CHUNK_SIZE", "5000"))
    
    logger.info("--- СТАРТ ОБРАБОТКИ ДАННЫХ ---")
    
    # Очищаем временный файл
    df_empty = pd.DataFrame(columns=['id', 'title', 'overview_word_count'])
    df_empty.to_csv(TEMP_FILE, index=False)

    total_source_rows = int(pd.read_sql("SELECT COUNT(*) AS cnt FROM movies", engine).iloc[0]["cnt"])
    logger.info(f"Источник movies: всего строк = {total_source_rows}, chunksize = {chunk_size}")

    query = "SELECT id, title, overview FROM movies ORDER BY id"
    started_at = time.time()
    chunk_no = 0
    
    # Читаем всю базу чанками
    for chunk in pd.read_sql(query, engine, chunksize=chunk_size):
        chunk_no += 1
        # Трансформация: считаем слова
        chunk['overview_word_count'] = chunk['overview'].apply(
            lambda x: len(str(x).split()) if pd.notnull(x) else 0
        )
        
        # Дописываем результат в CSV
        chunk[['id', 'title', 'overview_word_count']].to_csv(
            TEMP_FILE, mode='a', index=False, header=False
        )
        
        total_rows += len(chunk)
        elapsed = max(time.time() - started_at, 1e-6)
        rate = total_rows / elapsed
        percent = (total_rows / total_source_rows * 100) if total_source_rows else 100.0
        logger.info(
            f"Прогресс: chunk #{chunk_no}, chunk_rows={len(chunk)}, "
            f"processed={total_rows}/{total_source_rows} ({percent:.2f}%), "
            f"avg_rate={rate:.1f} rows/sec"
        )

    logger.info(f"--- ФИНИШ: Всего обработано {total_rows} строк ---")

def load_data():
    engine = create_engine(DB_URL)
    logger.info("Читаю временный файл для загрузки в БД...")
    
    df = pd.read_csv(TEMP_FILE)
    logger.info(f"Загружаю {len(df)} строк в таблицу movies_stats...")
    
    df.to_sql('movies_stats', engine, if_exists='replace', index=False)
    logger.info("--- ДАННЫЕ УСПЕШНО ЗАГРУЖЕНЫ В POSTGRES ---")

with DAG(
    dag_id='ml_rec_etl_pipeline', # Оставляем тот же ID
    start_date=datetime(2026, 3, 15),
    schedule=None,
    catchup=False,
    tags=['stage_2', 'kaggle_data']
) as dag:

    process_task = PythonOperator(
        task_id='process_movies_data',
        python_callable=extract_and_transform
    )

    load_task = PythonOperator(
        task_id='load_to_db',
        python_callable=load_data
    )

    process_task >> load_task