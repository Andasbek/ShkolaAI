import streamlit as st
import requests
import os
import json
import time
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8001")

st.set_page_config(
    page_title="Tech Support Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .reportview-container {
        margin-top: -2em;
    }
    .stDeployButton {display:none;}
    .main .block-container{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div.stButton > button:first-child {
        background-color: #0099ff;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #0077cc;
        color: white;
    }
    .chat-message {
        padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex
    }
    .chat-message.user {
        background-color: #2b313e
    }
    .chat-message.bot {
        background-color: #475063
    }
    .source-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        font-size: 0.9em;
        margin-top: 10px;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Tech Support Assistant")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/bot.png", width=100)
    st.markdown("### Status & Settings")
    
    api_status = "🔴 Offline"
    try:
        resp = requests.get(f"{API_URL}/health", timeout=1)
        if resp.status_code == 200:
            api_status = "🟢 Online"
    except:
        pass
    
    st.markdown(f"**Backend:** {api_status}")
    st.code(API_URL, language="text")
    st.divider()
    
    st.markdown("### About")
    st.info("Hybrid RAG System demonstrating Workflow vs Agentic approaches for technical support.")
    
# Tabs
tab_chat, tab_kb, tab_tickets = st.tabs(["💬 Support Chat", "📚 Knowledge Base", "📝 Ticket History"])

# --- TAB 1: SUPPORT CHAT ---
with tab_chat:
    # Header
    col_main, col_reset = st.columns([6, 1])
    with col_main:
        st.write("Discribe your issue, provide technical context, and choose your support mode.")
    with col_reset:
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    # Session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Inputs Layout
    with st.container():
        c1, c2 = st.columns([1, 2])
        with c1:
            mode = st.radio(
                "Processing Mode", 
                ["workflow", "agent"], 
                horizontal=True,
                help="Workflow: Fast, rigid pipeline. Agent: Smart, multi-step reasoning."
            )
            
        with c2:
            with st.expander("Technical Context (JSON)", expanded=False):
                default_context = '{\n  "os": "Ubuntu 22.04",\n  "error": "Connection refused",\n  "logs": "..."\n}'
                context_input = st.text_area("Provide extra context", value=default_context, height=150)
                # Validation
                try:
                    context_dict = json.loads(context_input)
                    st.caption("✅ Valid JSON")
                except json.JSONDecodeError:
                    context_dict = {}
                    st.caption("⚠️ Invalid JSON (Using empty context)")

    st.divider()

    # Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("How can I help you today?"):
        # 1. Add User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Add Assistant Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner(f"Thinking in {mode} mode..."):
                try:
                    payload = {
                        "question": prompt,
                        "context": context_dict,
                        "mode": mode
                    }
                    
                    start_time = time.time()
                    resp = requests.post(f"{API_URL}/support/query", json=payload, timeout=60)
                    latency = time.time() - start_time
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("answer", "No answer provided.")
                        ticket_id = data.get("ticket_id")
                        
                        # Formatting response
                        full_content = answer
                        
                        # Add Metadata Footer
                        footer = f"\n\n---\n<small>⏱️ {latency:.2f}s | 🎫 Ticket: `{ticket_id}` | ⚙️ Mode: `{mode}`</small>"
                        full_content += footer
                        
                        # Add Sources if present
                        if data.get("sources"):
                            full_content += "\n\n**📚 References:**"
                            for s in data["sources"]:
                                full_content += f"\n- [{s['title']}] (Score: {s.get('score', 0):.2f})"

                        message_placeholder.markdown(full_content, unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": full_content})
                        
                    else:
                        err = f"❌ Error {resp.status_code}: {resp.text}"
                        message_placeholder.error(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})

                except Exception as e:
                    st.error(f"Connection Failed: {e}")

# --- TAB 2: KNOWLEDGE BASE ---
with tab_kb:
    c_ingest, c_search = st.columns(2)
    
    with c_ingest:
        st.subheader("📥 Data Ingestion")
        st.markdown("Import documents from your local directory into the Vector DB.")
        
        kb_path_in = st.text_input("Source Directory", value="data/kb_docs")
        force_reindex = st.toggle("Force Full Re-index", value=True)
        
        if st.button("Start Ingestion Process", use_container_width=True):
            with st.status("Ingesting Knowledge Base...", expanded=True) as status:
                st.write("Requesting backend...")
                try:
                    resp = requests.post(
                        f"{API_URL}/kb/ingest", 
                        json={"path": kb_path_in, "reindex": force_reindex}
                    )
                    if resp.status_code == 200:
                        st.write("✅ Ingestion Triggered!")
                        st.write("⏳ Processing files in background...")
                        time.sleep(2)
                        status.update(label="Ingestion Started", state="complete")
                        st.success("Background process started successfully.")
                    else:
                        status.update(label="Ingestion Failed", state="error")
                        st.error(resp.text)
                except Exception as e:
                    st.error(f"Error: {e}")
                    
    with c_search:
        st.subheader("🔍 Vector Search Debugger")
        q = st.text_input("Test Query", placeholder="e.g. nginx error")
        top_k = st.slider("Results count", 1, 10, 3)
        
        if q and st.button("Search KB"):
            try:
                r = requests.get(f"{API_URL}/kb/search", params={"q": q, "k": top_k})
                results = r.json().get("results", [])
                
                for idx, item in enumerate(results):
                    doc = item['document']
                    with st.expander(f"#{idx+1} {doc['title']} (Score: {item['score']:.4f})"):
                        st.markdown(f"**Source:** `{doc['source']}`")
                        st.info(item['text'])
            except Exception as e:
                st.warning(f"Search failed: {e}")

# --- TAB 3: TICKET VIEWER ---
with tab_tickets:
    st.subheader("🕵️ Ticket Inspector")
    
    col_input, col_view = st.columns([1, 3])
    
    with col_input:
        tid = st.number_input("Ticket ID", min_value=1, step=1)
        load_btn = st.button("Inspect Ticket", use_container_width=True)
    
    if load_btn and tid:
        try:
            resp = requests.get(f"{API_URL}/tickets/{tid}")
            if resp.status_code == 200:
                ticket = resp.json()
                
                with col_view:
                    # Ticket Header Card
                    st.markdown(f"""
                    <div style="padding:20px; border:1px solid #ddd; border-radius:10px; margin-bottom:20px;">
                        <h3>Ticket #{ticket['id']}</h3>
                        <p><b>Status:</b> Completed</p>
                        <p><b>Question:</b> {ticket['question']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("### ✅ Final Answer")
                    st.markdown(ticket['answer'])
                    
                    # Agent Logs
                    if ticket.get("tool_logs"):
                        st.markdown("### 🤖 Agent Execution Trace")
                        for log in ticket["tool_logs"]:
                            with st.expander(f"Step {log['step']}: Used `{log['tool']}`"):
                                st.markdown("**Arguments:**")
                                st.json(log['input'])
                                st.markdown("**Output:**")
                                st.markdown(f"```\n{log['output']}\n```")
            else:
                st.error("Ticket not found.")
        except Exception as e:
            st.error(f"Error fetching ticket: {e}")
