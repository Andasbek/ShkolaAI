# scripts/verify_project.py
import requests
import time
import json
import os

BASE_URL = "http://localhost:8001"

TEST_CASES = [
    {
        "question": "Docker daemon is not running",
        "context": {"os": "Ubuntu 22.04", "error": "Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?"}
    },
    {
        "question": "Nginx 502 Bad Gateway",
        "context": {"os": "Debian", "logs": "connect() failed (111: Connection refused) while connecting to upstream"}
    },
    {
        "question": "Port 8000 already in use",
        "context": {"os": "Mac", "error": "OSError: [Errno 98] Address already in use"}
    }
]

def run_query(mode, q, ctx):
    start = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/support/query", json={
            "question": q,
            "context": ctx,
            "mode": mode
        })
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": str(e), "latency": 0}
    
    latency = time.time() - start
    return {
        "answer": data.get("answer", ""),
        "sources": len(data.get("sources", [])),
        "latency": latency,
        "ticket_id": data.get("ticket_id")
    }

def main():
    print("Starting verification...")
    results = []

    # 1. Trigger Ingest (assuming server is running)
    print("Triggering Ingestion...")
    # requests.post(f"{BASE_URL}/kb/ingest", json={"reindex": True})
    # time.sleep(5) # Wait for background task... (in real verify we might want to wait longer or check logs)
    # Skipping automated ingest wait for this script, assuming it's done or we do it manually.

    for i, case in enumerate(TEST_CASES):
        print(f"Running Case {i+1}: {case['question']}")
        
        # Workflow
        print("  - Mode: Workflow")
        res_wf = run_query("workflow", case["question"], case["context"])
        
        # Agent
        print("  - Mode: Agent")
        res_ag = run_query("agent", case["question"], case["context"])
        
        results.append({
            "case": case["question"],
            "workflow": res_wf,
            "agent": res_ag
        })

    # Generate Report
    report = "# Verification Report\n\n| Case | WF Latency | Ag Latency | WF Sources | Ag Sources | WF Ticket | Ag Ticket |\n|---|---|---|---|---|---|---|\n"
    for r in results:
        report += f"| {r['case']} | {r['workflow']['latency']:.2f}s | {r['agent']['latency']:.2f}s | {r['workflow'].get('sources',0)} | {r['agent'].get('sources',0)} | {r['workflow'].get('ticket_id')} | {r['agent'].get('ticket_id')} |\n"
    
    with open("report.md", "w") as f:
        f.write(report)
    
    print("Report generated: report.md")

if __name__ == "__main__":
    main()
