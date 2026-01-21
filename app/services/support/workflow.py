import json
import os
import structlog
from sqlalchemy.orm import Session
from app.db.models import Ticket
from app.services.kb.search import KBSearchService
import openai

logger = structlog.get_logger()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini" # or gpt-4-turbo

class WorkflowEngine:
    def __init__(self, db: Session):
        self.db = db
        self.search_service = KBSearchService(db)

    def run(self, question: str, context: dict) -> Ticket:
        # 1. Extract Signals & Classify (combined for speed or separate?)
        # Let's do separate logical steps but maybe one LLM call if optimizing. 
        # Requirement says "chain", implies steps.
        
        # Step 1: Analyze Input
        analysis = self._analyze_input(question, context)
        category = analysis.get("category", "general")
        keywords = analysis.get("keywords", [])
        
        # Step 2: Retrieve
        search_query = f"{question} {' '.join(keywords)}"
        kb_results = self.search_service.search(search_query, k=5)
        
        # Step 3: Generate Answer
        answer = self._generate_response(question, context, kb_results, analysis)
        
        # Step 4: Save Ticket
        ticket = Ticket(
            mode="workflow",
            question=question,
            context=context,
            category=category,
            answer=answer,
            sources=[{"title": r["document"]["title"], "source": r["document"]["source"]} for r in kb_results]
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def _analyze_input(self, question: str, context: dict) -> dict:
        prompt = f"""
        Analyze the following technical support query.
        Input: {question}
        Context: {json.dumps(context)}
        
        Return a JSON with:
        - category: (docker, nginx, postgres, python, etc.)
        - keywords: list of important terms/error codes
        - severity: (low, medium, high)
        """
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def _generate_response(self, question: str, context: dict, kb_results: list, analysis: dict) -> str:
        context_str = "\n".join([f"- {r['text']} (Source: {r['document']['title']})" for r in kb_results])
        
        prompt = f"""
        You are a Technical Support Engineer.
        User Query: {question}
        User Context: {json.dumps(context)}
        Detected Issue Category: {analysis.get('category')}
        
        Relevant Knowledge Base Articles:
        {context_str}
        
        Instructions:
        1. Diagnose the problem based on the knowledge base.
        2. Provide a step-by-step solution.
        3. Explain how to verify the fix.
        4. List what to provide if the issue persists.
        5. Cite sources if used.
        
        Format the output clearly in Markdown.
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
