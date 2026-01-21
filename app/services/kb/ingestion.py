import json
import os
import structlog
from typing import List, Dict, Any
import tiktoken
from sqlalchemy.orm import Session
from app.db.models import Document, Chunk
from app.db.database import SessionLocal
import openai

logger = structlog.get_logger()

# OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

def get_embedding(text: str) -> List[float]:
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=EMBEDDING_MODEL).data[0].embedding

class KBIngestor:
    def __init__(self, kb_path: str, db: Session):
        self.kb_path = kb_path
        self.db = db
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def load_index(self) -> List[Dict[str, Any]]:
        index_path = os.path.join(self.kb_path, "index.json")
        with open(index_path, "r") as f:
            return json.load(f)

    def split_text(self, text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:
        """
        Splits text into chunks of approximately `chunk_size` tokens.
        Simple implementation: split by generic separators, then regroup.
        """
        tokens = self.tokenizer.encode(text)
        total_tokens = len(tokens)
        chunks = []
        
        start = 0
        while start < total_tokens:
            end = min(start + chunk_size, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            if end == total_tokens:
                break
                
            start += chunk_size - chunk_overlap
            
        return chunks

    def ingest_all(self, reindex: bool = False, chunk_size: int = 800, chunk_overlap: int = 100):
        if reindex:
            logger.info("Clearing existing KB data...")
            self.db.query(Chunk).delete()
            self.db.query(Document).delete()
            self.db.commit()

        index_data = self.load_index()
        total_files = len(index_data)
        logger.info("Starting ingestion", total_files=total_files)

        for i, entry in enumerate(index_data):
            filename = entry["file"]
            file_path = os.path.join(self.kb_path, filename)
            
            if not os.path.exists(file_path):
                logger.warning("File not found, skipping", file=filename)
                continue

            with open(file_path, "r") as f:
                content = f.read()

            # Create Document
            doc = Document(
                title=entry.get("title", filename),
                category=entry.get("category", "unknown"),
                tags=entry.get("tags", []),
                source=os.path.join(self.kb_path, filename) # Saving full relative path or just filename?
            )
            self.db.add(doc)
            self.db.flush() # get ID

            # Create Chunks
            text_chunks = self.split_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            
            for idx, chunk_text in enumerate(text_chunks):
                # Generate embedding
                try:
                    embedding = get_embedding(chunk_text)
                except Exception as e:
                    logger.error("Embedding failed", error=str(e), chunk_index=idx, file=filename)
                    continue

                chunk_obj = Chunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    embedding=embedding,
                    metadata_={
                        "file": filename,
                        "category": doc.category,
                        "tags": doc.tags
                    }
                )
                self.db.add(chunk_obj)
            
            self.db.commit()
            if (i + 1) % 10 == 0:
                logger.info("Processed files", count=i+1)

        logger.info("Ingestion complete")

def ingest_kb(path: str, reindex: bool = True, chunk_size: int = 800, chunk_overlap: int = 100):
    db = SessionLocal()
    try:
        ingestor = KBIngestor(path, db)
        ingestor.ingest_all(reindex, chunk_size, chunk_overlap)
    finally:
        db.close()
