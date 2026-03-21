import pandas as pd
import numpy as np
import ast
import psycopg2
import json
import time
import os
import mlflow
from psycopg2.extras import execute_values
from tqdm.auto import tqdm

# Используем переменные окружения для работы в Docker (с фоллбэком на локальные значения)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"), 
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "movies_db"),
    "user": os.getenv("DB_USER", "user"),
    "password": os.getenv("DB_PASSWORD", "password")
}

# Настройка MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("Movie_Recommendations_Pipeline")

print("[1/6] Загрузка и обработка CSV...", flush=True)
df = pd.read_csv('./data/lesson36_data/movies_metadata.csv', low_memory=False, on_bad_lines='skip')

# Оставляем только нужные колонки и чистим пропуски
df = df[['title', 'overview', 'genres']].dropna(subset=['title', 'overview'])
df = df.drop_duplicates(subset=['overview']).reset_index(drop=True)

def extract_genres(genre_str):
    try:
        genres_list = ast.literal_eval(genre_str)
        return ", ".join([g['name'] for g in genres_list])
    except:
        return ""

# Парсим жанры и склеиваем текст
df['clean_genres'] = df['genres'].apply(extract_genres)
df['combined_text'] = "Title: " + df['title'] + ". Genres: " + df['clean_genres'] + ". Overview: " + df['overview']

print(f"[2/6] Подготовлено фильмов: {len(df)}", flush=True)

def upload_data(embeddings_matrix):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    records = []
    for i in range(len(df)):
        records.append((
            df.iloc[i]['title'],
            df.iloc[i]['clean_genres'],
            df.iloc[i]['overview'],
            df.iloc[i]['combined_text'],
            embeddings_matrix[i].tolist()
        ))
    
    insert_query = """
        INSERT INTO movies (title, genres, overview, combined_text, embedding)
        VALUES %s
    """
    
    batch_size = 500
    for i in tqdm(range(0, len(records), batch_size), desc="Запись в БД"):
        batch = records[i:i+batch_size]
        execute_values(cur, insert_query, batch)
        conn.commit()
    
    cur.close()
    conn.close()
    print("Данные успешно перенесены в PostgreSQL!")

# ==========================================
# ОСНОВНОЙ БЛОК MLFLOW
# ==========================================
model_name = 'all-MiniLM-L6-v2'
batch_size_encode = 64

# Запускаем трекинг
with mlflow.start_run(run_name="Data_Processing_and_Embedding"):
    # Логируем параметры
    mlflow.log_param("model_name", model_name)
    mlflow.log_param("dataset_size", len(df))
    mlflow.log_param("batch_size", batch_size_encode)
    
    print(f"[3/6] Импорт sentence-transformers...", flush=True)
    from sentence_transformers import SentenceTransformer

    print(f"[4/6] Загрузка модели {model_name}", flush=True)
    model = SentenceTransformer(model_name, device='cpu')
    
    print("[5/6] Генерация эмбеддингов...", flush=True)
    start_encode_time = time.time()
    embeddings = model.encode(
        df['combined_text'].tolist(), 
        batch_size=batch_size_encode, 
        show_progress_bar=True, 
        convert_to_numpy=True
    )
    encode_duration = time.time() - start_encode_time
    
    # Логируем метрику времени генерации
    mlflow.log_metric("encoding_time_seconds", encode_duration)
    print(f"Матрица векторов готова: {embeddings.shape}. Время: {encode_duration:.2f} сек.", flush=True)
    
    print("[6/6] Загрузка данных в БД...", flush=True)
    start_db_time = time.time()
    upload_data(embeddings)
    db_duration = time.time() - start_db_time
    
    # Логируем метрику времени загрузки
    mlflow.log_metric("db_upload_time_seconds", db_duration)
    
print("Пайплайн завершен, метрики отправлены в MLflow.", flush=True)
# ==========================================

# Функция рекомендаций остается без изменений (только использует обновленный DB_CONFIG)
def get_recommendations_and_log(source_title, top_n=5):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT combined_text FROM movies WHERE title = %s LIMIT 1;", (source_title,))
    result = cur.fetchone()
    if not result:
        return "Фильм не найден в базе."
    
    source_text = result[0]
    
    # Модель берем глобальную, она уже загружена выше
    query_vector = model.encode([source_text])[0].tolist()
    
    search_query = """
        SELECT title, genres, 1 - (embedding <=> %s::vector) AS similarity
        FROM movies
        WHERE title != %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    cur.execute(search_query, (query_vector, source_title, query_vector, top_n))
    recs = cur.fetchall()
    
    recommendations_data = []
    print(f"\nРекомендации для фильма: {source_title}\n" + "-"*40)
    
    for row in recs:
        title, genres, sim = row
        score_percent = round(max(0, sim) * 100, 1)
        print(f"{title} ({score_percent}%) | Жанры: {genres}")
        recommendations_data.append({"title": title, "match": score_percent})
    
    log_query = """
        INSERT INTO recommendation_logs (source_title, source_text, recommendations)
        VALUES (%s, %s, %s)
    """
    cur.execute(log_query, (source_title, source_text, json.dumps(recommendations_data)))
    conn.commit()
    
    cur.close()
    conn.close()
    print("\n[Результат сохранен в БД в таблицу recommendation_logs]")

random_movie = df['title'].sample(5).values[0]
get_recommendations_and_log(random_movie)