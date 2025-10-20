# frontend.py
import streamlit as st
import requests
import uuid
from datetime import datetime
import json  # ← NEW
import os  # ← NEW

st.set_page_config(page_title="Order Support Chat", page_icon="🛍️", layout="wide")

# API URL
API_URL = "http://localhost:8000/chat"

# ===== PERSISTENCE SETUP ===== ← NEW SECTION
THREADS_FILE = "threads.json"  # ← NEW


def save_threads():  # ← NEW FUNCTION
    """Save threads to file"""
    with open(THREADS_FILE, 'w') as f:
        json.dump(st.session_state.threads, f, indent=2)


def load_threads():  # ← NEW FUNCTION
    """Load threads from file"""
    if os.path.exists(THREADS_FILE):
        with open(THREADS_FILE, 'r') as f:
            return json.load(f)
    return None


# ===== Initialize Session State ===== ← MODIFIED SECTION
if "threads" not in st.session_state:
    # Try to load saved threads ← NEW
    loaded = load_threads()  # ← NEW

    if loaded:  # ← NEW
        st.session_state.threads = loaded  # ← NEW
    else:  # ← NEW - Only create default if no saved data
        # Dictionary to store all threads
        st.session_state.threads = {
            str(uuid.uuid4()): {
                "name": "New Conversation",
                "messages": [],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "customer_email": ""
            }
        }

if "active_thread_id" not in st.session_state:
    # Set the first thread as active
    st.session_state.active_thread_id = list(st.session_state.threads.keys())[0]


# ===== Helper Functions =====

def create_new_thread():
    """Create a new conversation thread"""
    new_thread_id = str(uuid.uuid4())
    st.session_state.threads[new_thread_id] = {
        "name": f"Conversation {len(st.session_state.threads) + 1}",
        "messages": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "customer_email": ""
    }
    st.session_state.active_thread_id = new_thread_id
    save_threads()  # ← NEW - Save after creating thread
    st.rerun()


def delete_thread(thread_id):
    """Delete a conversation thread"""
    if len(st.session_state.threads) > 1:
        del st.session_state.threads[thread_id]
        # Switch to another thread
        st.session_state.active_thread_id = list(st.session_state.threads.keys())[0]
        save_threads()  # ← NEW - Save after deleting thread
        st.rerun()


def switch_thread(thread_id):
    """Switch to a different thread"""
    st.session_state.active_thread_id = thread_id
    st.rerun()


def rename_thread(thread_id, new_name):
    """Rename a thread"""
    st.session_state.threads[thread_id]["name"] = new_name
    save_threads()  # ← NEW - Save after renaming


# Get active thread
active_thread = st.session_state.threads[st.session_state.active_thread_id]

# ===== Sidebar: Thread Management =====
with st.sidebar:
    st.header("💬 Conversations")

    # New conversation button
    if st.button("➕ New Conversation", use_container_width=True, type="primary"):
        create_new_thread()

    st.divider()

    # List all threads
    for thread_id, thread_data in st.session_state.threads.items():
        is_active = thread_id == st.session_state.active_thread_id

        # Create a container for each thread
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                # Thread button
                if st.button(
                        f"{'🔵' if is_active else '⚪'} {thread_data['name'][:20]}",
                        key=f"thread_{thread_id}",
                        use_container_width=True,
                        disabled=is_active
                ):
                    switch_thread(thread_id)

            with col2:
                # Delete button (only if more than 1 thread)
                if len(st.session_state.threads) > 1:
                    if st.button("🗑️", key=f"del_{thread_id}"):
                        delete_thread(thread_id)

            # Show message count and time
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
        save_threads()  # ← NEW - Save when email changes

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
st.title(f"🛍️ {active_thread['name']}")
st.caption("Ask me about your orders, returns, or order status!")

# Display chat history for active thread
for message in active_thread["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message...", key=f"input_{st.session_state.active_thread_id}"):

    if not customer_email:
        st.warning("⚠️ Please enter your email in the sidebar first!")
    else:
        # Add user message to active thread
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
                            "session_id": st.session_state.active_thread_id  # Use thread ID as session ID
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

        # Add assistant response to active thread
        active_thread["messages"].append({"role": "assistant", "content": response_text})

        # Auto-rename first conversation based on first message
        if len(active_thread["messages"]) == 2 and active_thread["name"].startswith("New Conversation"):
            # Use first few words of user's first message as thread name
            first_message = prompt[:30] + ("..." if len(prompt) > 30 else "")
            rename_thread(st.session_state.active_thread_id, first_message)

        save_threads()  # ← NEW - Save after each message exchange
        st.rerun()

# Show empty state if no messages
if len(active_thread["messages"]) == 0:
    st.info("👋 Start a conversation! Ask me about your orders.")

    # Quick action buttons
    st.markdown("### Quick Actions:")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📦 Check Order Status"):
            st.session_state.quick_action = "What's the status of my order?"

    with col2:
        if st.button("🔄 View My Orders"):
            st.session_state.quick_action = "Show me all my orders"

    with col3:
        if st.button("↩️ Return Item"):
            st.session_state.quick_action = "I want to return an item"