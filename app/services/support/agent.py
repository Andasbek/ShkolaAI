import json
import os
import structlog
from sqlalchemy.orm import Session
from app.db.models import Ticket, ToolLog
from app.services.kb.search import KBSearchService
import openai

logger = structlog.get_logger()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

class AgentEngine:
    def __init__(self, db: Session):
        self.db = db
        self.search_service = KBSearchService(db)

    def run(self, question: str, context: dict) -> Ticket:
        # Create Ticket first to log steps
        ticket = Ticket(
            mode="agent",
            question=question,
            context=context,
            category="pending"
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        messages = [
            {"role": "system", "content": """You are an advanced Tech Support Agent. 
            Your goal is to diagnose and solve the user's issue using the available tools.
            1. Analyze the issue.
            2. Search the knowledge base.
            3. if needed, refined search or ask for clarification (simulated).
            4. Provide a final answer in the required format.
            """},
            {"role": "user", "content": f"Question: {question}\nContext: {json.dumps(context)}"}
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "kb_search",
                    "description": "Search the knowledge base for relevant articles.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "classify_issue",
                    "description": "Classify the issue category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Category name (e.g. docker, nginx)"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]}
                        },
                        "required": ["category"]
                    }
                }
            }
        ]

        steps = 0
        max_steps = 8
        final_answer = ""
        sources = []

        while steps < max_steps:
            steps += 1
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            msg = response.choices[0].message
            messages.append(msg)

            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    # Log tool usage
                    self._log_tool_step(ticket.id, steps, func_name, args)

                    tool_result = ""
                    if func_name == "kb_search":
                        results = self.search_service.search(args["query"])
                        tool_result = json.dumps([{
                            "text": r["text"][:200] + "...", 
                            "title": r["document"]["title"]
                        } for r in results])
                        # Collect sources
                        for r in results:
                            sources.append({"title": r["document"]["title"], "source": r["document"]["source"]})
                            
                    elif func_name == "classify_issue":
                        ticket.category = args["category"]
                        self.db.commit()
                        tool_result = f"Classified as {args['category']}"

                    # Append tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                    
                    # Update tool log with output
                    self._update_tool_log_output(ticket.id, steps, tool_result)
            else:
                # No tool calls, presumably final answer
                final_answer = msg.content
                break
        
        ticket.answer = final_answer
        # De-duplicate sources
        ticket.sources = [dict(t) for t in {tuple(d.items()) for d in sources}]
        self.db.commit()
        return ticket

    def _log_tool_step(self, ticket_id, step, tool_name, tool_input):
        log = ToolLog(
            ticket_id=ticket_id,
            step=step,
            tool_name=tool_name,
            tool_input=tool_input
        )
        self.db.add(log)
        self.db.commit()

    def _update_tool_log_output(self, ticket_id, step, output):
        # In a real scenario we'd query by ID, but simplified here by assuming order or looking up last
        # Actually safer to just filter by ticket_id & step
        log = self.db.query(ToolLog).filter_by(ticket_id=ticket_id, step=step).first()
        if log:
            log.tool_output = output
            self.db.commit()
