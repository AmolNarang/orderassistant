# app/agent.py
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver  # ← ADD THIS
from app.database import SessionLocal, Order, Customer, ReturnRequest, Product
from datetime import datetime
from typing import Dict
import random

# app/agent.py - Add this new tool
from config import API_KEY
from sqlalchemy import text
import json


@tool
def query_database(question: str) -> dict:
    """
    Write and execute SQL queries to answer analytical questions about orders,
    customers, products, and returns.

    Use this tool ONLY when asked analytical questions like:
    - "How many orders...?"
    - "Which customer...?"
    - "What's the most...?"
    - "Show me all..."
    - "List customers who..."

    DO NOT use this for individual order lookups - use get_order_status instead.

    Args:
        question: The analytical question to answer
    """

    db = SessionLocal()

    try:
        # Generate SQL query using LLM
        sql_query = generate_sql_from_question(question)

        # Validate and execute
        result = execute_safe_query(db, sql_query)

        return {
            "success": True,
            "question": question,
            "sql_query": sql_query,
            "results": result["data"],
            "row_count": result["count"],
            "explanation": result["explanation"]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "I couldn't execute that query. Please rephrase your question."
        }

    finally:
        db.close()


def generate_sql_from_question(question: str) -> str:
    """
    Use LLM to generate SQL query from natural language question.
    """

    # Database schema information
    schema_info = """
    DATABASE SCHEMA:

    Table: customers
    - id (INTEGER, PRIMARY KEY)
    - name (TEXT)
    - email (TEXT, UNIQUE)
    - phone (TEXT)

    Table: orders
    - id (TEXT, PRIMARY KEY) - Format: ORD001, ORD002
    - customer_id (INTEGER, FOREIGN KEY -> customers.id)
    - total (REAL)
    - status (TEXT) - Values: 'pending', 'shipped', 'delivered', 'cancelled'
    - order_date (DATETIME)

    Table: products
    - id (INTEGER, PRIMARY KEY)
    - sku (TEXT, UNIQUE) - Format: SKU001, SKU002
    - name (TEXT)
    - price (REAL)

    Table: order_items
    - id (INTEGER, PRIMARY KEY)
    - order_id (TEXT, FOREIGN KEY -> orders.id)
    - product_id (INTEGER, FOREIGN KEY -> products.id)
    - quantity (INTEGER)

    Table: returns
    - id (TEXT, PRIMARY KEY) - Format: RET1234
    - order_id (TEXT, FOREIGN KEY -> orders.id)
    - product_sku (TEXT)
    - reason (TEXT)
    - status (TEXT) - Values: 'pending', 'approved', 'completed'
    - created_at (DATETIME)

    RELATIONSHIPS:
    - customers.id -> orders.customer_id (one-to-many)
    - orders.id -> order_items.order_id (one-to-many)
    - products.id -> order_items.product_id (one-to-many)
    - orders.id -> returns.order_id (one-to-many)
    """

    prompt = f"""You are a SQL expert. Generate a READ-ONLY SQL query to answer the question.

{schema_info}

RULES:
1. Use ONLY SELECT statements (no INSERT, UPDATE, DELETE, DROP, etc.)
2. Use proper JOINs when accessing multiple tables
3. Use aggregate functions (COUNT, SUM, AVG) when appropriate
4. Limit results to 10 rows unless specifically asked for more
5. Use clear column aliases
6. Return ONLY the SQL query, nothing else

Question: {question}

SQL Query:"""

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=API_KEY,
        temperature=0
    )

    response = llm.invoke(prompt)

    # Extract SQL query (remove markdown formatting if present)
    sql_query = response.content.strip()
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

    return sql_query


def execute_safe_query(db, sql_query: str) -> dict:
    """
    Execute SQL query with safety checks.
    """

    # Security: Block dangerous operations
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER',
        'CREATE', 'TRUNCATE', 'REPLACE', 'GRANT', 'REVOKE'
    ]

    query_upper = sql_query.upper()
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            raise ValueError(f"Dangerous operation detected: {keyword}")

    # Execute query
    result = db.execute(text(sql_query))

    # Fetch results
    rows = result.fetchall()
    columns = result.keys() if hasattr(result, 'keys') else []

    # Format as list of dictionaries
    data = []
    for row in rows:
        data.append(dict(zip(columns, row)))

    # Generate explanation
    explanation = generate_result_explanation(sql_query, data)

    return {
        "data": data,
        "count": len(data),
        "explanation": explanation
    }


def generate_result_explanation(sql_query: str, data: list) -> str:
    """
    Generate human-readable explanation of query results.
    """

    if not data:
        return "No results found."

    # Simple explanation based on query type
    if "COUNT" in sql_query.upper():
        count_value = list(data[0].values())[0] if data else 0
        return f"Found {count_value} records matching your criteria."

    elif "SUM" in sql_query.upper():
        sum_value = list(data[0].values())[0] if data else 0
        return f"Total sum: ${sum_value:.2f}" if isinstance(sum_value, (int, float)) else f"Total: {sum_value}"

    elif "AVG" in sql_query.upper():
        avg_value = list(data[0].values())[0] if data else 0
        return f"Average value: {avg_value:.2f}" if isinstance(avg_value, (int, float)) else f"Average: {avg_value}"

    else:
        return f"Retrieved {len(data)} record(s)."

# app/agent.py - Add this tool

from app.knowledge_base import get_knowledge_base

# Initialize knowledge base (do this once)
knowledge_base = get_knowledge_base()


@tool
def search_company_knowledge(query: str) -> str:
    """
    Search company policies, FAQs, and product information.
    Use this when customer asks about:
    - Return/refund policies
    - Shipping information
    - Product specifications
    - General company policies
    - How-to questions

    Args:
        query: What to search for
    """

    # Search vector store
    results = knowledge_base.similarity_search(query, k=3)

    if not results:
        return "No relevant information found in company knowledge base."

    # Format results
    context = "\n\n".join([
        f"**Source: {doc.metadata.get('type', 'unknown')}**\n{doc.page_content}"
        for doc in results
    ])

    return context

# ===== Keep all your existing tools (get_order_status, initiate_return, list_customer_orders) =====
# ... (same as before)

@tool
def get_order_status(order_id: str, customer_email: str) -> Dict:
    """
    Get order status and details. Requires order ID and customer email.

    Args:
        order_id: The order ID (e.g., ORD001)
        customer_email: Customer's email for verification
    """
    db = SessionLocal()

    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return {
                "success": False,
                "message": f"Order {order_id} not found in our system."
            }

        if order.customer.email.lower() != customer_email.lower():
            return {
                "success": False,
                "message": "The email doesn't match our records for this order."
            }

        items = []
        for item in order.items:
            items.append({
                "name": item.product.name,
                "sku": item.product.sku,
                "quantity": item.quantity,
                "price": item.product.price
            })

        return {
            "success": True,
            "order_id": order.id,
            "status": order.status,
            "order_date": order.order_date.strftime("%Y-%m-%d"),
            "total": f"${order.total:.2f}",
            "items": items,
            "customer_name": order.customer.name
        }

    finally:
        db.close()


@tool
def initiate_return(order_id: str, product_sku: str, reason: str, customer_email: str) -> Dict:
    """
    Initiate a return request for a product.

    Args:
        order_id: The order ID
        product_sku: Product SKU to return (e.g., SKU001)
        reason: Reason for return
        customer_email: Customer's email for verification
    """
    db = SessionLocal()

    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return {"success": False, "message": f"Order {order_id} not found."}

        if order.customer.email.lower() != customer_email.lower():
            return {"success": False, "message": "Email doesn't match order records."}

        product_in_order = False
        for item in order.items:
            if item.product.sku == product_sku:
                product_in_order = True
                break

        if not product_in_order:
            return {
                "success": False,
                "message": f"Product {product_sku} not found in order {order_id}."
            }

        days_since_order = (datetime.utcnow() - order.order_date).days
        if days_since_order > 30:
            return {
                "success": False,
                "message": f"Return window has expired. Order was placed {days_since_order} days ago (limit: 30 days)."
            }

        return_id = f"RET{random.randint(1000, 9999)}"
        return_req = ReturnRequest(
            id=return_id,
            order_id=order_id,
            product_sku=product_sku,
            reason=reason,
            status="pending"
        )
        db.add(return_req)
        db.commit()

        return {
            "success": True,
            "return_id": return_id,
            "message": f"Return request created successfully! Return ID: {return_id}. We'll email you a return label within 24 hours.",
            "next_steps": "Pack the item in its original packaging and wait for the return label."
        }

    finally:
        db.close()


@tool
def list_customer_orders(customer_email: str) -> Dict:
    """
    List all orders for a customer.

    Args:
        customer_email: Customer's email address
    """
    db = SessionLocal()

    try:
        customer = db.query(Customer).filter(Customer.email == customer_email).first()

        if not customer:
            return {
                "success": False,
                "message": "No customer found with that email."
            }

        orders = []
        for order in customer.orders:
            orders.append({
                "order_id": order.id,
                "status": order.status,
                "total": f"${order.total:.2f}",
                "date": order.order_date.strftime("%Y-%m-%d"),
                "items_count": len(order.items)
            })

        return {
            "success": True,
            "customer_name": customer.name,
            "orders": orders
        }

    finally:
        db.close()


# ===== UPDATED: Agent Creation with Memory =====

def create_agent(api_key: str):
    """Create the order management agent with memory"""

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=api_key,
        temperature=0.3
    )

    tools = [
        get_order_status,
        search_company_knowledge,
        initiate_return,
        list_customer_orders
    ]

    # ✅ ADD MEMORY HERE
    memory = MemorySaver()

    agent = create_react_agent(
        llm,
        tools,
        checkpointer=memory  # ← This enables conversation memory!
    )

    return agent


SYSTEM_PROMPT = """You are a friendly and helpful customer service agent for an e-commerce company.

Your capabilities:
- Check order status
- Help customers initiate returns
- View customer's order history

Note:
1. For policy/general questions, use search_company_knowledge FIRST
2. For order-specific actions, use the order tools

When using search_company_knowledge:
- Always search before answering policy questions
- Quote the exact policy when relevant
- Combine knowledge base info with order data

Important guidelines:
1. Always ask for the customer's email if they haven't provided it yet
2. Be empathetic and professional
3. Provide clear, concise responses
4. If a customer wants to return something, explain they have 30 days from order date
5. Always verify the customer's email matches the order before showing details
6. Remember previous conversation context - if the customer mentioned their email or order ID earlier, use that information

Keep your responses friendly and conversational!
"""