# frontend.py - Add toggle button

import streamlit as st
import requests
import uuid
from datetime import datetime
import json
import os

st.set_page_config(page_title="Order Support Chat", page_icon="🛍️", layout="wide")

API_URL = "http://localhost:8000/chat"

# ===== Persistence Setup =====
THREADS_FILE = "threads.json"


def save_threads():
    with open(THREADS_FILE, 'w') as f:
        json.dump(st.session_state.threads, f, indent=2)


def load_threads():
    if os.path.exists(THREADS_FILE):
        with open(THREADS_FILE, 'r') as f:
            return json.load(f)
    return None


# ===== Initialize Session State =====
if "threads" not in st.session_state:
    loaded = load_threads()

    if loaded:
        st.session_state.threads = loaded
    else:
        st.session_state.threads = {
            str(uuid.uuid4()): {
                "name": "New Conversation",
                "messages": [],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "customer_email": ""
            }
        }

if "active_thread_id" not in st.session_state:
    st.session_state.active_thread_id = list(st.session_state.threads.keys())[0]

# ===== NEW: Initialize SQL toggle =====
if "enable_sql_queries" not in st.session_state:
    st.session_state.enable_sql_queries = False


# ===== Helper Functions =====

def create_new_thread():
    new_thread_id = str(uuid.uuid4())
    st.session_state.threads[new_thread_id] = {
        "name": f"Conversation {len(st.session_state.threads) + 1}",
        "messages": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "customer_email": ""
    }
    st.session_state.active_thread_id = new_thread_id
    save_threads()
    st.rerun()


def delete_thread(thread_id):
    if len(st.session_state.threads) > 1:
        del st.session_state.threads[thread_id]
        st.session_state.active_thread_id = list(st.session_state.threads.keys())[0]
        save_threads()
        st.rerun()


def switch_thread(thread_id):
    st.session_state.active_thread_id = thread_id
    st.rerun()


def rename_thread(thread_id, new_name):
    st.session_state.threads[thread_id]["name"] = new_name
    save_threads()


# Get active thread
active_thread = st.session_state.threads[st.session_state.active_thread_id]

# ===== Sidebar =====
with st.sidebar:
    st.header("💬 Conversations")

    if st.button("➕ New Conversation", use_container_width=True, type="primary"):
        create_new_thread()

    st.divider()

    # List all threads
    for thread_id, thread_data in st.session_state.threads.items():
        is_active = thread_id == st.session_state.active_thread_id

        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                if st.button(
                        f"{'🔵' if is_active else '⚪'} {thread_data['name'][:20]}",
                        key=f"thread_{thread_id}",
                        use_container_width=True,
                        disabled=is_active
                ):
                    switch_thread(thread_id)

            with col2:
                if len(st.session_state.threads) > 1:
                    if st.button("🗑️", key=f"del_{thread_id}"):
                        delete_thread(thread_id)

            if is_active:
                st.caption(f"📝 {len(thread_data['messages'])} messages • {thread_data['created_at']}")

    st.divider()

    # ===== Customer Info for Active Thread =====
    st.header("👤 Customer Info")

    # Customer email (stored per thread)
    customer_email = st.text_input(
        "Your Email:",
        value=active_thread["customer_email"],
        placeholder="your@example.com",
        help="We need this to verify your orders",
        key=f"email_{st.session_state.active_thread_id}"
    )

    # Update thread's email
    if customer_email != active_thread["customer_email"]:
        st.session_state.threads[st.session_state.active_thread_id]["customer_email"] = customer_email
        save_threads()

    st.divider()

    # ===== NEW: SQL QUERY TOGGLE =====
    st.header("🔧 Features")

    sql_enabled = st.toggle(
        "💾 Chat with Your Data",
        value=st.session_state.enable_sql_queries,
        help="Enable database queries for analytics (e.g., 'How many returns are active?')"
    )

    if sql_enabled != st.session_state.enable_sql_queries:
        st.session_state.enable_sql_queries = sql_enabled
        st.rerun()

    # Show feature status
    if st.session_state.enable_sql_queries:
        st.success("✅ SQL Queries Enabled")
        st.caption("You can now ask analytical questions!")
    else:
        st.info("ℹ️ SQL Queries Disabled")
        st.caption("Enable to ask database questions")

    st.divider()
    st.subheader("🧪 Test Emails")
    st.code("john@example.com")
    st.code("jane@example.com")
    st.code("bob@example.com")

    st.divider()

    # Rename current conversation
    with st.expander("✏️ Rename Conversation"):
        new_name = st.text_input(
            "New name:",
            value=active_thread["name"],
            key="rename_input"
        )
        if st.button("Save Name"):
            rename_thread(st.session_state.active_thread_id, new_name)
            st.success("Renamed!")
            st.rerun()

    # Thread details
    st.caption(f"Thread ID: {st.session_state.active_thread_id[:8]}...")

# ===== Main Chat Area =====

# Header with SQL status indicator
col1, col2 = st.columns([3, 1])
with col1:
    st.title(f"🛍️ {active_thread['name']}")
with col2:
    if st.session_state.enable_sql_queries:
        st.markdown("### 💾 SQL ON")

st.caption("Ask me about your orders, returns, or order status!")

# Display chat history
for message in active_thread["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ===== Show example queries when SQL is enabled =====
if st.session_state.enable_sql_queries and len(active_thread["messages"]) == 0:
    st.info("💾 **SQL Mode Active** - Try asking analytical questions!")

    st.markdown("### 📊 Example Queries:")

    example_queries = [
        "How many return requests are active?",
        "Which customer has placed the most orders?",
        "What's the total revenue from all orders?",
        "List all pending orders",
        "Which product has been returned the most?",
        "How many orders were delivered last week?"
    ]

    cols = st.columns(2)
    for idx, query in enumerate(example_queries):
        with cols[idx % 2]:
            if st.button(f"💡 {query}", key=f"example_{idx}", use_container_width=True):
                # Set the query as if user typed it
                st.session_state.example_query = query

# Chat input
if prompt := st.chat_input("Type your message...", key=f"input_{st.session_state.active_thread_id}"):

    if not customer_email and not st.session_state.enable_sql_queries:
        st.warning("⚠️ Please enter your email in the sidebar first!")
    else:
        # Add user message
        active_thread["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call API
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        API_URL,
                        json={
                            "message": prompt,
                            "customer_email": customer_email,
                            "session_id": st.session_state.active_thread_id,
                            "enable_sql_queries": st.session_state.enable_sql_queries  # ← SEND TOGGLE
                        },
                        timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        response_text = data["response"]
                    else:
                        response_text = f"❌ Error: {response.status_code}"

                except Exception as e:
                    response_text = f"❌ Error connecting to API: {str(e)}"

            st.markdown(response_text)

        # Add assistant response
        active_thread["messages"].append({"role": "assistant", "content": response_text})

        # Auto-rename
        if len(active_thread["messages"]) == 2 and active_thread["name"].startswith("New Conversation"):
            first_message = prompt[:30] + ("..." if len(prompt) > 30 else "")
            rename_thread(st.session_state.active_thread_id, first_message)

        save_threads()
        st.rerun()

# Handle example query clicks
if "example_query" in st.session_state:
    prompt = st.session_state.example_query
    del st.session_state.example_query
    st.rerun()