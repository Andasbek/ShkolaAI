#!/bin/bash
# Enable venv
source venv/bin/activate
# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
