# frontend_advanced.py
import streamlit as st
import requests
import uuid
from datetime import datetime

st.set_page_config(page_title="Order Support Chat", page_icon="🛍️", layout="wide")

API_URL = "http://localhost:8000/chat"

# ===== CSS Styling =====
st.markdown("""
<style>
    .thread-item {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
        cursor: pointer;
    }
    .thread-active {
        background-color: #e6f3ff;
        border-left: 3px solid #1f77b4;
    }
    .thread-inactive {
        background-color: #f0f0f0;
    }
    .thread-inactive:hover {
        background-color: #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# ===== Initialize Session State =====
if "threads" not in st.session_state:
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


# ===== Helper Functions =====

def create_new_thread():
    """Create a new conversation thread"""
    new_thread_id = str(uuid.uuid4())
    st.session_state.threads[new_thread_id] = {
        "name": "New Conversation",
        "messages": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "customer_email": ""
    }
    st.session_state.active_thread_id = new_thread_id


def delete_thread(thread_id):
    """Delete a conversation thread"""
    if len(st.session_state.threads) > 1:
        del st.session_state.threads[thread_id]
        st.session_state.active_thread_id = list(st.session_state.threads.keys())[0]


def get_thread_preview(messages):
    """Get last message preview"""
    if not messages:
        return "No messages yet"
    last_msg = messages[-1]
    preview = last_msg["content"][:40]
    return preview + "..." if len(last_msg["content"]) > 40 else preview


# Get active thread
active_thread = st.session_state.threads[st.session_state.active_thread_id]

# ===== Sidebar =====
with st.sidebar:
    st.header("💬 Conversations")

    if st.button("➕ New Conversation", use_container_width=True, type="primary"):
        create_new_thread()
        st.rerun()

    st.divider()

    # Sort threads by creation time (newest first)
    sorted_threads = sorted(
        st.session_state.threads.items(),
        key=lambda x: x[1]["created_at"],
        reverse=True
    )

    for thread_id, thread_data in sorted_threads:
        is_active = thread_id == st.session_state.active_thread_id

        # Thread container
        container = st.container()

        with container:
            cols = st.columns([6, 1])

            with cols[0]:
                # Thread button with emoji indicator
                button_label = f"{'🟢' if is_active else '⚪'} **{thread_data['name']}**"

                if st.button(
                        button_label,
                        key=f"switch_{thread_id}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"
                ):
                    if not is_active:
                        st.session_state.active_thread_id = thread_id
                        st.rerun()

                # Show preview and metadata
                st.caption(f"💬 {len(thread_data['messages'])} msgs • {thread_data['created_at']}")
                if thread_data['messages']:
                    st.caption(f"_{get_thread_preview(thread_data['messages'])}_")

            with cols[1]:
                if len(st.session_state.threads) > 1:
                    if st.button("🗑️", key=f"delete_{thread_id}", help="Delete thread"):
                        delete_thread(thread_id)
                        st.rerun()

            st.divider()

    # ===== Customer Info =====
    st.header("👤 Customer Info")

    customer_email = st.text_input(
        "Email:",
        value=active_thread["customer_email"],
        placeholder="your@example.com",
        key=f"email_input"
    )

    if customer_email != active_thread["customer_email"]:
        st.session_state.threads[st.session_state.active_thread_id]["customer_email"] = customer_email

    st.divider()

    # Test data
    with st.expander("🧪 Test Data"):
        st.code("john@example.com\nORD001")
        st.code("jane@example.com\nORD002")
        st.code("bob@example.com\nORD003")

    # Thread management
    with st.expander("⚙️ Thread Settings"):
        new_name = st.text_input(
            "Rename:",
            value=active_thread["name"]
        )
        if st.button("Save"):
            st.session_state.threads[st.session_state.active_thread_id]["name"] = new_name
            st.success("✅ Saved!")
            st.rerun()

        st.caption(f"ID: {st.session_state.active_thread_id[:8]}...")

        if st.button("🧹 Clear Messages"):
            st.session_state.threads[st.session_state.active_thread_id]["messages"] = []
            st.rerun()

# ===== Main Chat Area =====
col1, col2 = st.columns([3, 1])

with col1:
    st.title(f"💬 {active_thread['name']}")

with col2:
    st.metric("Messages", len(active_thread["messages"]))

st.caption("AI-powered order support chatbot")
st.divider()

# Display messages
for idx, message in enumerate(active_thread["messages"]):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about orders, returns, or shipping..."):

    if not customer_email:
        st.error("⚠️ Please enter your email in the sidebar first!")
    else:
        # Add user message
        active_thread["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    response = requests.post(
                        API_URL,
                        json={
                            "message": prompt,
                            "customer_email": customer_email,
                            "session_id": st.session_state.active_thread_id
                        },
                        timeout=30
                    )

                    if response.status_code == 200:
                        response_text = response.json()["response"]
                    else:
                        response_text = f"❌ Error: {response.status_code}"

                except Exception as e:
                    response_text = f"❌ Connection error: {str(e)}"

            st.markdown(response_text)

        # Add assistant message
        active_thread["messages"].append({"role": "assistant", "content": response_text})

        # Auto-rename based on first message
        if len(active_thread["messages"]) == 2 and "New Conversation" in active_thread["name"]:
            auto_name = prompt[:35] + ("..." if len(prompt) > 35 else "")
            st.session_state.threads[st.session_state.active_thread_id]["name"] = auto_name

        st.rerun()

# Empty state
if not active_thread["messages"]:
    st.info("👋 Welcome! How can I help you today?")

    st.markdown("### 🚀 Quick Actions")

    col1, col2, col3 = st.columns(3)

    example_prompts = [
        "📦 Check my order status",
        "📋 Show all my orders",
        "↩️ I want to return an item"
    ]

    for col, prompt in zip([col1, col2, col3], example_prompts):
        with col:
            if st.button(prompt, use_container_width=True):
                # Simulate user clicking the prompt
                pass

# Footer
st.divider()
st.caption(
    f"💡 Active Thread: {st.session_state.active_thread_id[:8]}... | Total Threads: {len(st.session_state.threads)}")