from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    category = Column(String, index=True)
    tags = Column(JSON, default=[])
    source = Column(String)  # file path relative to project root
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_index = Column(Integer)
    chunk_text = Column(Text)
    # Dimension will assume 1536 for OpenAI embeddings implicitly or can be dynamic
    embedding = Column(Vector()) 
    metadata_ = Column("metadata", JSON, default={}) # 'metadata' is reserved in Base
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String, index=True) # workflow | agent
    question = Column(Text)
    context = Column(JSON, default={})
    answer = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    sources = Column(JSON, default=[])
    latency_ms = Column(Float, nullable=True)
    token_usage = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tool_logs = relationship("ToolLog", back_populates="ticket", cascade="all, delete-orphan")

class ToolLog(Base):
    __tablename__ = "tool_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    step = Column(Integer)
    tool_name = Column(String)
    tool_input = Column(JSON)
    tool_output = Column(Text) # or JSON, but Text is more flexible for varied outputs
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="tool_logs")
