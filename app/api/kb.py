from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.kb.ingestion import ingest_kb
from app.services.kb.search import KBSearchService

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

class IngestRequest(BaseModel):
    path: str = "data/kb_docs"
    reindex: bool = True
    chunk_size: int = 800
    chunk_overlap: int = 100

class SearchResponse(BaseModel):
    results: list

@router.post("/ingest")
def ingest_endpoint(req: IngestRequest, background_tasks: BackgroundTasks):
    # Running in background to avoid timeout
    background_tasks.add_task(ingest_kb, req.path, req.reindex, req.chunk_size, req.chunk_overlap)
    return {"message": "Ingestion started in background"}

@router.get("/search")
def search_endpoint(q: str, k: int = 5, db: Session = Depends(get_db)):
    service = KBSearchService(db)
    results = service.search(q, k)
    return {"results": results}
