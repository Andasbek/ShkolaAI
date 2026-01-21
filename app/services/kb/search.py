import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Chunk, Document
from app.services.kb.ingestion import get_embedding
import structlog

logger = structlog.get_logger()

class KBSearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        # Embed query
        query_embedding = get_embedding(query)

        # Search using cosine distance operator <=>
        stmt = select(Chunk, Document).join(Document).order_by(
            Chunk.embedding.cosine_distance(query_embedding)
        ).limit(k)

        results = self.db.execute(stmt).all()
        
        output = []
        for chunk, doc in results:
            output.append({
                "chunk_id": chunk.id,
                "text": chunk.chunk_text,
                "document": {
                    "title": doc.title,
                    "source": doc.source,
                    "category": doc.category
                },
                "score": 0.0 # TODO: Calculate score if needed, or return distance
            })
        
        return output
