#  Audio Preprocessing for ML & DL

## Содержание
В ноутбуке рассмотрены 6 ключевых блоков:

### 1.  Основы и Физика
* Загрузка аудио (`librosa`), Resampling.
* Теорема Котельникова, Алиасинг и выбор Sample Rate.

### 2. Спектральные представления (Time-Frequency)
* **STFT:** Математика Фурье и выбор окна.
* **Mel-Spectrogram:** Главный стандарт для Deep Learning (CNN, Transformers).
* **Log-Mel:** Переход к децибелам.

### 3.  Тембральные и Кепстральные признаки
* **MFCC:** Классика для распознавания речи (ASR).
* **Spectral Contrast:** Текстура звука.
* **HPSS:** Разделение на Гармоники (мелодию) и Перкуссию (ритм).

### 4. Музыкальные признаки
* **Chroma:** Определение нот и аккордов.
* **Tonnetz:** Гармонические отношения (интервалы).

### 5. Статистические признаки (Handcrafted)
* ZCR (шумность), RMS (энергия), Spectral Centroid (яркость).
* Диагностика аудиосигналов.

### 6. Аугментация данных
* Time Stretch, Pitch Shift, Noise Injection.
* **SpecAugment:** Маскирование частот/времени для нейросетей.



## Quick Start

1. **Установка зависимостей:**
```conda
pip install librosa numpy matplotlib pandas ipython
