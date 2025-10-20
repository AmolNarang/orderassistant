import json
import os
import random
from typing import Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from config import MODEL_NAME, API_KEY, langsmith_key

# Set up LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = langsmith_key  # Set this as env variable
os.environ["LANGCHAIN_PROJECT"] = "order-management-agent"

# =====================
# DUMMY DATA & TOOLS
# =====================

# Dummy order database
DUMMY_ORDERS = {
    "ORD001": {
        "id": "ORD001",
        "customer": "John Doe",
        "items": [{"sku": "SKU123", "name": "Wireless Headphones", "price": 49.99}],
        "status": "delivered",
        "order_date": "2025-10-01"
    },
    "ORD002": {
        "id": "ORD002",
        "customer": "Jane Smith",
        "items": [{"sku": "SKU456", "name": "USB-C Cable", "price": 15.99}],
        "status": "pending",
        "order_date": "2025-10-10"
    },
    "ORD003": {
        "id": "ORD003",
        "customer": "Bob Johnson",
        "items": [{"sku": "SKU789", "name": "Phone Case", "price": 25.00}],
        "status": "shipped",
        "order_date": "2025-10-05"
    }
}

# Store for escalations and requests
escalations = []
return_requests = []
replacement_requests = []


# =====================
# TOOL DEFINITIONS
# =====================

@tool
def get_order_status(order_id: str) -> dict:
    """Get the current status of an order by order ID."""
    if order_id in DUMMY_ORDERS:
        order = DUMMY_ORDERS[order_id]
        return {
            "success": True,
            "order_id": order_id,
            "status": order["status"],
            "items": order["items"],
            "order_date": order["order_date"],
            "message": f"Order {order_id} is currently {order['status']}"
        }
    else:
        return {
            "success": False,
            "order_id": order_id,
            "message": f"Order {order_id} not found in system"
        }


@tool
def initiate_return(order_id: str, item_sku: str, reason: str) -> dict:
    """Initiate a return request for an item in an order."""
    if order_id not in DUMMY_ORDERS:
        return {
            "success": False,
            "message": f"Order {order_id} not found"
        }

    order = DUMMY_ORDERS[order_id]

    # Check if item exists in order
    item_found = any(item["sku"] == item_sku for item in order["items"])

    if not item_found:
        return {
            "success": False,
            "message": f"Item {item_sku} not found in order {order_id}"
        }

    # Create return request
    return_req = {
        "return_id": f"RET{random.randint(10000, 99999)}",
        "order_id": order_id,
        "item_sku": item_sku,
        "reason": reason,
        "status": "pending_approval"
    }

    return_requests.append(return_req)

    return {
        "success": True,
        "return_id": return_req["return_id"],
        "message": f"Return request initiated. Return ID: {return_req['return_id']}. We will review your request and send further instructions.",
        "details": return_req
    }


@tool
def initiate_replacement(order_id: str, item_sku: str) -> dict:
    """Initiate a replacement request for a defective item."""
    if order_id not in DUMMY_ORDERS:
        return {
            "success": False,
            "message": f"Order {order_id} not found"
        }

    order = DUMMY_ORDERS[order_id]

    # Check if item exists in order
    item_found = any(item["sku"] == item_sku for item in order["items"])

    if not item_found:
        return {
            "success": False,
            "message": f"Item {item_sku} not found in order {order_id}"
        }

    # Create replacement request
    replacement_req = {
        "replacement_id": f"REP{random.randint(10000, 99999)}",
        "order_id": order_id,
        "item_sku": item_sku,
        "status": "pending_processing"
    }

    replacement_requests.append(replacement_req)

    return {
        "success": True,
        "replacement_id": replacement_req["replacement_id"],
        "message": f"Replacement request created. Replacement ID: {replacement_req['replacement_id']}. We will process and ship your replacement within 3-5 business days.",
        "details": replacement_req
    }


@tool
def escalate_to_human(conversation_summary: str, reason: str) -> dict:
    """Escalate the conversation to a human agent."""
    escalation = {
        "escalation_id": f"ESC{random.randint(10000, 99999)}",
        "reason": reason,
        "conversation_summary": conversation_summary,
        "status": "waiting_for_agent"
    }

    escalations.append(escalation)

    return {
        "success": True,
        "escalation_id": escalation["escalation_id"],
        "message": f"Your case has been escalated to a human agent. Escalation ID: {escalation['escalation_id']}. A team member will contact you shortly."
    }


# =====================
# AGENT SETUP
# =====================

def create_order_agent():
    """Create and return the order management agent."""

    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=API_KEY
    )

    # Define tools
    tools = [
        get_order_status,
        initiate_return,
        initiate_replacement,
        escalate_to_human
    ]

    # Create the agent
    agent = create_react_agent(llm, tools)

    return agent


def run_agent(user_query: str):
    """Run the agent with a user query."""

    agent = create_order_agent()

    # System message for the agent
    system_message = """You are a helpful customer service agent for an e-commerce company. 
    You help customers with:
    1. Checking order status
    2. Processing return requests
    3. Processing replacement requests
    4. Escalating complex issues to human agents

    Be friendly, professional, and concise. Ask clarifying questions if needed.
    If a customer has a complex issue you cannot resolve with available tools, escalate to a human agent.
    """

    # Create messages
    messages = [
        HumanMessage(content=f"{system_message}\n\nCustomer: {user_query}")
    ]

    # Run the agent
    result = agent.invoke({"messages": messages})

    # Extract the response
    response = result["messages"][-1].content

    return response


# =====================
# MAIN EXECUTION
# =====================

if __name__ == "__main__":
    # Example queries
    queries = [
        "What's the status of my order ORD001?",
        "I want to return item SKU123 from order ORD001 because it's broken",
        "Can I get a replacement for item SKU456 in order ORD002?",
        "I have a very complex issue with my order that I can't resolve"
    ]

    print("=" * 60)
    print("ORDER MANAGEMENT AGENT DEMO")
    print("=" * 60)

    for query in queries:
        print(f"\n👤 Customer: {query}")
        print("-" * 60)
        response = run_agent(query)
        print(f"🤖 Agent: {response}")
        print()

    # Print summary of created requests
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Return Requests: {len(return_requests)}")
    for ret in return_requests:
        print(f"  - {ret['return_id']}: {ret['reason']}")

    print(f"\nReplacement Requests: {len(replacement_requests)}")
    for rep in replacement_requests:
        print(f"  - {rep['replacement_id']}")

    print(f"\nEscalations: {len(escalations)}")
    for esc in escalations:
        print(f"  - {esc['escalation_id']}: {esc['reason']}")