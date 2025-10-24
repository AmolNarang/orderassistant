# shop.py - NEW FILE (Simple shopping interface)

import streamlit as st
import requests

st.set_page_config(page_title="Product Shop", page_icon="🛒", layout="wide")

API_URL = "http://localhost:8000"

# Initialize cart in session state
if "cart" not in st.session_state:
    st.session_state.cart = {}


# ===== Helper Functions =====

def add_to_cart(sku, name, price):
    """Add item to cart"""
    if sku in st.session_state.cart:
        st.session_state.cart[sku]["quantity"] += 1
    else:
        st.session_state.cart[sku] = {
            "name": name,
            "price": price,
            "quantity": 1
        }


def remove_from_cart(sku):
    """Remove item from cart"""
    if sku in st.session_state.cart:
        del st.session_state.cart[sku]


def update_quantity(sku, quantity):
    """Update item quantity"""
    if quantity <= 0:
        remove_from_cart(sku)
    else:
        st.session_state.cart[sku]["quantity"] = quantity


def get_cart_total():
    """Calculate cart total"""
    return sum(item["price"] * item["quantity"] for item in st.session_state.cart.values())


def clear_cart():
    """Clear entire cart"""
    st.session_state.cart = {}


# ===== Main UI =====

st.title("🛒 Product Shop")
st.caption("Browse products and place orders")

# Create tabs
tab1, tab2 = st.tabs(["🛍️ Shop", "🛒 Cart"])

# ===== TAB 1: Product Catalog =====
with tab1:
    st.header("Available Products")

    # Fetch products
    try:
        response = requests.get(f"{API_URL}/products", timeout=5)

        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])

            if not products:
                st.info("No products available")
            else:
                # Display products in grid
                cols = st.columns(3)

                for idx, product in enumerate(products):
                    with cols[idx % 3]:
                        with st.container(border=True):
                            st.subheader(product["name"])
                            st.write(f"**SKU:** {product['sku']}")
                            st.write(f"**Price:** ${product['price']:.2f}")

                            # Stock indicator
                            stock = product.get("stock", 10)
                            if stock > 5:
                                st.success(f"✅ In Stock ({stock} available)")
                            elif stock > 0:
                                st.warning(f"⚠️ Low Stock ({stock} left)")
                            else:
                                st.error("❌ Out of Stock")

                            # Add to cart button
                            if stock > 0:
                                if st.button(
                                        "🛒 Add to Cart",
                                        key=f"add_{product['sku']}",
                                        use_container_width=True
                                ):
                                    add_to_cart(
                                        product['sku'],
                                        product['name'],
                                        product['price']
                                    )
                                    st.success(f"Added {product['name']} to cart!")
                                    st.rerun()
        else:
            st.error(f"Error loading products: {response.status_code}")

    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        st.info("💡 Make sure the API is running: `uvicorn app.main:app --reload`")

# ===== TAB 2: Shopping Cart =====
with tab2:
    st.header("Your Cart")

    if not st.session_state.cart:
        st.info("🛒 Your cart is empty")
        st.caption("Go to the Shop tab to add products")
    else:
        # Display cart items
        for sku, item in st.session_state.cart.items():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.write(f"**{item['name']}**")
                st.caption(f"SKU: {sku}")

            with col2:
                st.write(f"${item['price']:.2f}")

            with col3:
                # Quantity selector
                new_qty = st.number_input(
                    "Qty",
                    min_value=0,
                    max_value=10,
                    value=item['quantity'],
                    key=f"qty_{sku}",
                    label_visibility="collapsed"
                )
                if new_qty != item['quantity']:
                    update_quantity(sku, new_qty)
                    st.rerun()

            with col4:
                if st.button("🗑️", key=f"remove_{sku}"):
                    remove_from_cart(sku)
                    st.rerun()

            st.divider()

        # Cart summary
        total = get_cart_total()

        st.markdown("### Cart Summary")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Items", sum(item['quantity'] for item in st.session_state.cart.values()))

        with col2:
            st.metric("Total", f"${total:.2f}")

        # Checkout form
        st.markdown("### 📋 Checkout")

        with st.form("checkout_form"):
            col1, col2 = st.columns(2)

            with col1:
                customer_name = st.text_input("Full Name *", placeholder="John Doe")
                customer_email = st.text_input("Email *", placeholder="john@example.com")

            with col2:
                customer_phone = st.text_input("Phone (Optional)", placeholder="+1 234 567 8900")

            # Order notes
            st.text_area("Order Notes (Optional)", placeholder="Any special instructions...")

            col1, col2 = st.columns([1, 1])

            with col1:
                submit_button = st.form_submit_button(
                    "🎉 Place Order",
                    use_container_width=True,
                    type="primary"
                )

            with col2:
                if st.form_submit_button("🗑️ Clear Cart", use_container_width=True):
                    clear_cart()
                    st.rerun()

        # Handle order submission
        if submit_button:
            if not customer_name or not customer_email:
                st.error("❌ Please fill in your name and email")
            else:
                # Prepare order data
                cart_items = [
                    {"product_sku": sku, "quantity": item["quantity"]}
                    for sku, item in st.session_state.cart.items()
                ]

                order_data = {
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "items": cart_items
                }

                # Place order
                with st.spinner("Processing your order..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/orders/place",
                            json=order_data,
                            timeout=10
                        )

                        if response.status_code == 200:
                            data = response.json()

                            if data["success"]:
                                st.success(f"✅ {data['message']}")
                                st.balloons()

                                # Show order details
                                st.markdown("### 📦 Order Confirmation")
                                st.info(f"""
                                **Order ID:** {data['order_id']}  
                                **Total:** ${data['total']:.2f}  
                                **Status:** Pending

                                We've sent a confirmation email to {customer_email}

                                💡 You can now check this order in the chatbot!
                                """)

                                # Clear cart
                                clear_cart()

                                # Show chatbot link
                                st.markdown("---")
                                st.markdown("### 🤖 Track Your Order")
                                st.info(
                                    f"Go to the chatbot and ask:\n\n`What's the status of order {data['order_id']}?`")
                            else:
                                st.error(f"❌ {data['message']}")
                        else:
                            st.error(f"Error: {response.status_code}")

                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")

# ===== Sidebar: Quick Stats =====
with st.sidebar:
    st.header("🛒 Cart Summary")

    if st.session_state.cart:
        st.metric("Items in Cart", sum(item['quantity'] for item in st.session_state.cart.values()))
        st.metric("Cart Total", f"${get_cart_total():.2f}")
    else:
        st.info("Cart is empty")

    st.divider()

    st.header("📞 Need Help?")
    st.info("Visit the chatbot to:\n- Check order status\n- Initiate returns\n- Ask questions")

    if st.button("💬 Go to Chatbot", use_container_width=True):
        st.info("Open `frontend.py` to chat with the support agent!")