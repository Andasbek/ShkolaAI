from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict
from app.db.database import get_db
from app.db.models import Ticket
from app.services.support.workflow import WorkflowEngine
from app.services.support.agent import AgentEngine

router = APIRouter(prefix="/support", tags=["Support"])

class SupportQuery(BaseModel):
    question: str
    context: Optional[Dict] = {}
    mode: str = "workflow"  # workflow or agent

@router.post("/query")
def support_query(req: SupportQuery, db: Session = Depends(get_db)):
    if req.mode == "workflow":
        engine = WorkflowEngine(db)
        ticket = engine.run(req.question, req.context)
    elif req.mode == "agent":
        engine = AgentEngine(db)
        ticket = engine.run(req.question, req.context)
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. use 'workflow' or 'agent'")
    
    return {"ticket_id": ticket.id, "answer": ticket.answer, "sources": ticket.sources}


