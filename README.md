# Tech Support Assistant (RAG Helpdesk)

A hybrid support system offering both deterministic **Workflow** processing and autonomous **Agent** resolution for technical issues, featuring a Streamlit UI.

## Features
- **KB Ingestion**: Parses Markdown files, chunks them, and stores embeddings in PostgreSQL (`pgvector`).
- **Workflow Mode**: Pipeline approach (Signals -> Classify -> Retrieve -> Generate).
- **Agent Mode**: LLM-driven agent using tools (`kb_search`, `classify`, etc.) to solve complex problems.
- **Comparison**: Tracks performance and logic differences between modes.
- **Streamlit UI**: Enhanced dashboard with dark mode, JSON context validation, and detailed agent log inspector.

## Setup

1. **Prerequisites**
   - Python 3.10+
   - PostgreSQL with `pgvector` extension.
   - OpenAI API Key.

2. **Installation**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Environment**
   Copy `.env.example` to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   # Edit .env
   ```
   **Note**: The default database port is **5434**.

4. **Database**
   Start the pgvector container:
   ```bash
   docker run --name pg-vector -e POSTGRES_PASSWORD=postgres -p 5434:5432 -d ankane/pgvector
   ```

## Usage

### 1. Start Services
Run the Backend API:
```bash
./run.sh
# Runs on http://localhost:8001
```

Run the Frontend UI:
```bash
./run_ui.sh
# Runs on http://localhost:8501
```

### 2. Use the UI
Open `http://localhost:8501` in your browser.
1.  Go to **Dashboard & KB** and click **Trigger Ingestion**.
2.  Go to **Support Chat** to talk to the assistant.

### 3. API Usage (Optional)
**Ingest KB**:
```bash
curl -X POST "http://localhost:8001/kb/ingest" \
     -H "Content-Type: application/json" \
     -d '{"path": "data/kb_docs", "reindex": true}'
```

**Support Query**:
```bash
curl -X POST "http://localhost:8001/support/query" \
     -H "Content-Type: application/json" \
     -d '{
           "question": "Nginx returning 502 error",
           "context": {"logs": "connect refused"},
           "mode": "agent"
         }'
```

## Verification
Run the verification script to compare Workflow vs Agent:
```bash
venv/bin/python scripts/verify_project.py
```

### Benchmark Results (Example)
| Case | Workflow Latency | Agent Latency |
|---|---|---|
| Docker daemon problem | ~16s | ~9s |
| Nginx 502 error | ~20s | ~11s |
| Port in use error | ~10s | ~12s |

## Documentation
See detailed documentation in [docs/documentation.md](docs/documentation.md).