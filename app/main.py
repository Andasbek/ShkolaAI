from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api import kb, support, tickets
from app.db.database import init_db
import structlog

logger = structlog.get_logger()

app = FastAPI(title="Tech Support Assistant")

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(kb.router)
app.include_router(support.router)
app.include_router(tickets.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
