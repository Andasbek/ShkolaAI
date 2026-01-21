#!/bin/bash
source venv/bin/activate
export API_URL="http://localhost:8001"
streamlit run app/frontend/streamlit_app.py --server.port 8501
