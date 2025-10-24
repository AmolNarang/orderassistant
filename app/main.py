# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agent import create_agent, get_system_prompt
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

# Store agents with different capabilities
agents_cache = {
    "basic": create_agent(API_KEY, enable_sql_queries=False),
    "sql": create_agent(API_KEY, enable_sql_queries=True)
}

# app/main.py - Add these new endpoints

from typing import List
from datetime import datetime
import random

# Add to existing imports
from app.database import Product, Order, OrderItem, Customer
from app.database import SessionLocal
from app.database import get_db

# ===== NEW: Order Placement Models =====

class CartItem(BaseModel):
    product_sku: str
    quantity: int


class PlaceOrderRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str = ""
    items: List[CartItem]


class PlaceOrderResponse(BaseModel):
    success: bool
    order_id: str = None
    total: float = None
    message: str


# ===== NEW: Endpoints =====

@app.get("/products")
async def get_products():
    """Get all available products"""
    db = next(get_db())

    try:
        products = db.query(Product).all()

        return {
            "success": True,
            "products": [
                {
                    "id": p.id,
                    "sku": p.sku,
                    "name": p.name,
                    "price": p.price,
                    "stock": getattr(p, 'stock_quantity', 10)  # Default stock
                }
                for p in products
            ]
        }
    finally:
        db.close()


@app.post("/orders/place", response_model=PlaceOrderResponse)
async def place_order(request: PlaceOrderRequest):
    """Place a new order"""


    db = SessionLocal()

    try:
        # Get or create customer
        customer = db.query(Customer).filter(Customer.email == request.customer_email).first()

        if not customer:
            customer = Customer(
                name=request.customer_name,
                email=request.customer_email,
                phone=request.customer_phone
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

        # Calculate total and validate products
        total = 0.0
        order_items_data = []

        for item in request.items:
            product = db.query(Product).filter(Product.sku == item.product_sku).first()

            if not product:
                return PlaceOrderResponse(
                    success=False,
                    message=f"Product {item.product_sku} not found"
                )

            item_total = product.price * item.quantity
            total += item_total

            order_items_data.append({
                "product": product,
                "quantity": item.quantity
            })

        # Generate order ID
        existing_orders = db.query(Order).count()
        order_id = f"ORD{str(existing_orders + 1).zfill(3)}"

        # Create order
        new_order = Order(
            id=order_id,
            customer_id=customer.id,
            total=total,
            status="pending",
            order_date=datetime.utcnow()
        )
        db.add(new_order)

        # Create order items
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data["product"].id,
                quantity=item_data["quantity"]
            )
            db.add(order_item)

        db.commit()

        return PlaceOrderResponse(
            success=True,
            order_id=order_id,
            total=total,
            message=f"Order placed successfully! Your order ID is {order_id}"
        )

    except Exception as e:
        db.rollback()
        return PlaceOrderResponse(
            success=False,
            message=f"Error placing order: {str(e)}"
        )

    finally:
        db.close()


# Add import at top if not already there


# ===== UPDATED: Request/Response models =====

class ChatRequest(BaseModel):
    message: str
    customer_email: str = ""
    session_id: str = None
    enable_sql_queries: bool = False  # ← NEW TOGGLE


class ChatResponse(BaseModel):
    response: str
    session_id: str  # ← ADD THIS


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with optional SQL query capability"""

    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    # Select agent based on toggle
    agent = agents_cache["sql"] if request.enable_sql_queries else agents_cache["basic"]
    system_prompt = get_system_prompt(request.enable_sql_queries)

    # Prepare message with customer email context
    user_message = request.message
    if request.customer_email:
        # Include email in the message context
        user_message = f"[Customer Email: {request.customer_email}]\n{request.message}"

    # ✅ IMPORTANT: Use config to specify the thread_id (session)
    config = {"configurable": {"thread_id": session_id}}

    # Check if new session
    try:
        state = agent.get_state(config)
        is_new_session = len(state.values.get("messages", [])) == 0
    except:
        is_new_session = True

    # Prepare messages
    messages = []
    if is_new_session:
        messages.append(SystemMessage(content=system_prompt))

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