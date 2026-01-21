# Документация проекта Tech Support Assistant (RAG Helpdesk)

Tech Support Assistant — это гибридная система технической поддержки, использующая технологии RAG (Retrieval-Augmented Generation). Система включает в себя Backend API и Frontend UI (Streamlit), поддерживая два режима работы: детерминированный **Workflow** и автономный **Agent**.

---

## 1. Обзор архитектуры

Проект построен на современном стеке технологий:

*   **Backend**: Python, FastAPI.
*   **Frontend**: Streamlit.
*   **Database**: PostgreSQL + `pgvector` (Векторный поиск).
*   **AI**: OpenAI API (`gpt-4o-mini` для логики, `text-embedding-3-small` для поиска).
*   **ORM**: SQLAlchemy.

### Основные компоненты

1.  **KB Ingestion (База знаний)**
    - Загружает Markdown-файлы из папки `data/kb_docs/`.
    - Разбивает текст на чанки (~800 токенов).
    - Генерирует эмбеддинги и сохраняет их в Postgres.

2.  **Support Engine (Движок поддержки)**
    *   **Workflow Mode**: Линейный конвейер. Быстрый и предсказуемый.
        1.  Анализ запроса.
        2.  Поиск по KB.
        3.  Генерация ответа.
    *   **Agent Mode**: ReAct агент. Гибкий и автономный.
        - Использует инструменты (`kb_search`, `classify_issue`).
        - Может выполнять многошаговый поиск.
        - Сохраняет логи действий.

3.  **User Interface (Streamlit)**
    - Веб-интерфейс с улучшенным UX (Dark mode, Custom CSS).
    - **Support Chat**: Валидация JSON контекста, цветовое кодирование сообщений, кнопка очистки.
    - **Dashboard**: Управление индексацией с индикатором прогресса.
    - **Ticket Viewer**: Детальный просмотр логов агента с группировкой шагов.

---

## 2. Установка и Настройка

### Предварительные требования
- Docker (для БД).
- Python 3.10+.
- OpenAI API Key.

### Шаг 1: Настройка окружения

1.  Клонируйте репозиторий и создайте venv:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

2.  Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

3.  Настройте `.env`:
    ```bash
    cp .env.example .env
    ```
    Укажите ваш API ключ и настройки БД.
    > **Важно**: В данном проекте база данных настроена на порт **5434**, чтобы избежать конфликтов с локальным Postgres.
    ```ini
    DATABASE_URL=postgresql://postgres:user_password@localhost:5434/rag_helpdesk
    ```

### Шаг 2: Запуск Базы Данных

Запустите контейнер с pgvector на порту 5434:
```bash
docker run --name pg-vector -e POSTGRES_PASSWORD=postgres -p 5434:5432 -d ankane/pgvector
```
При первом запуске приложения база `rag_helpdesk` будет создана автоматически (или можно создать вручную через `createdb`).

### Шаг 3: Запуск Проекта

Вам потребуется два терминала.

**Терминал 1: Backend API**
```bash
./run.sh
```
Запускает FastAPI сервер на `http://localhost:8001`.

**Терминал 2: Frontend UI**
```bash
./run_ui.sh
```
Запускает Streamlit приложение на `http://localhost:8501`.

---

## 3. Использование

### 3.1 Веб-интерфейс (Рекомендуемы)

Откройте `http://localhost:8501`.

1.  **Вкладка "Dashboard & KB"**:
    - Введите путь к данным (по умолчанию `data/kb_docs`).
    - Нажмите **Trigger Ingestion** для загрузки базы знаний.
    - Используйте **Test Search** для проверки поиска.

2.  **Вкладка "Support Chat"**:
    - Выберите режим: **Workflow** или **Agent**.
    - Введите контекст (JSON) и описание проблемы.
    - Получите ответ с диагнозом и решением.

3.  **Вкладка "Ticket Viewer"**:
    - Введите ID тикета, чтобы посмотреть детальный ответ и логи агента (какие инструменты использовались, что нашлось в базе).

### 3.2 API Методы

Если вы хотите использовать API напрямую:

*   `POST /kb/ingest`: Индексация базы.
*   `GET /kb/search`: Поиск.
*   `POST /support/query`: Создание запроса (возвращает ответ и ID тикета).
*   `GET /tickets/{id}`: Получение деталей тикета.

---

## 4. Тестирование

Для проверки качества работы системы предусмотрен скрипт верификации.

```bash
venv/bin/python scripts/verify_project.py
```

Скрипт прогонит 8 тестовых сценариев (Docker, Nginx, Linux и т.д.) через оба режима (Workflow и Agent) и создаст сравнительный отчет `report.md`.

### Пример результатов (Benchmark)

| Сценарий | Workflow Latency | Agent Latency |
|---|---|---|
| Docker daemon problem | ~16s | ~9s |
| Nginx 502 error | ~20s | ~11s |
| Port in use error | ~10s | ~12s |

---

## 5. Структура проекта

```
.
├── app/
│   ├── api/            # API Endpoints
│   ├── db/             # Models & Database setup
│   ├── frontend/       # Streamlit App
│   ├── services/       # Core Logic (KB, Workflow, Agent)
│   └── main.py         # FastAPI Entrypoint
├── data/kb_docs/       # Knowledge Base markdown files
├── docs/               # Documentation
├── scripts/            # Helper scripts
├── requirements.txt    # Dependencies
├── run.sh              # Start API
└── run_ui.sh           # Start UI
```
