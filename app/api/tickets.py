from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Ticket

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.get("/{id}")
def get_ticket(id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {
        "id": ticket.id,
        "question": ticket.question,
        "answer": ticket.answer,
        "sources": ticket.sources,
        "tool_logs": [{"step": log.step, "tool": log.tool_name, "input": log.tool_input, "output": log.tool_output} for log in ticket.tool_logs]
    }
