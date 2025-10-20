# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agent import create_agent, SYSTEM_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage
from config import API_KEY, langsmith_key
import uuid


# Set up LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = langsmith_key  # Set this as env variable
os.environ["LANGCHAIN_PROJECT"] = "order-agent-2"


app = FastAPI(title="Simple Order Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent (only once)
agent = create_agent(API_KEY)


# ===== UPDATED: Request/Response models with session =====

class ChatRequest(BaseModel):
    message: str
    customer_email: str = ""
    session_id: str = None  # ← ADD THIS


class ChatResponse(BaseModel):
    response: str
    session_id: str  # ← ADD THIS


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with session management"""

    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    # Prepare message with customer email context
    user_message = request.message
    if request.customer_email:
        # Include email in the message context
        user_message = f"[Customer Email: {request.customer_email}]\n{request.message}"

    # ✅ IMPORTANT: Use config to specify the thread_id (session)
    config = {"configurable": {"thread_id": session_id}}

    # On first message of a session, include system prompt
    # Check if this is a new session by trying to get state
    try:
        state = agent.get_state(config)
        is_new_session = len(state.values.get("messages", [])) == 0
    except:
        is_new_session = True

    # Prepare messages
    messages = []
    if is_new_session:
        messages.append(SystemMessage(content=SYSTEM_PROMPT))

    messages.append(HumanMessage(content=user_message))

    # Run agent with memory
    result = agent.invoke(
        {"messages": messages},
        config=config  # ← This maintains conversation state!
    )

    # Extract response
    response_text = result["messages"][-1].content

    return ChatResponse(
        response=response_text,
        session_id=session_id
    )


@app.get("/")
async def root():
    return {"message": "Order Agent API is running!", "status": "healthy"}


@app.get("/health")
async def health():
    return {"status": "ok"}