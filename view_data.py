from app.database import SessionLocal, Customer, Product, Order, OrderItem, ReturnRequest


def view_data():
    db = SessionLocal()

    # Fetch and print all customers
    customers = db.query(Customer).all()
    print("Customers:")
    for customer in customers:
        print(f"ID: {customer.id}, Name: {customer.name}, Email: {customer.email}, Phone: {customer.phone}")

    # Fetch and print all products
    products = db.query(Product).all()
    print("\nProducts:")
    for product in products:
        print(f"ID: {product.id}, SKU: {product.sku}, Name: {product.name}, Price: {product.price}")

    # Fetch and print all orders
    orders = db.query(Order).all()
    print("\nOrders:")
    for order in orders:
        print(
            f"ID: {order.id}, Customer ID: {order.customer_id}, Total: {order.total}, Status: {order.status}, Order Date: {order.order_date}")

    # Fetch and print all order items
    order_items = db.query(OrderItem).all()
    print("\nOrder Items:")
    for item in order_items:
        print(f"ID: {item.id}, Order ID: {item.order_id}, Product ID: {item.product_id}, Quantity: {item.quantity}")

    # Fetch and print all return requests (if any)
    returns = db.query(ReturnRequest).all()
    print("\nReturn Requests:")
    for return_request in returns:
        print(
            f"ID: {return_request.id}, Order ID: {return_request.order_id}, Product SKU: {return_request.product_sku}, Reason: {return_request.reason}, Status: {return_request.status}, Created At: {return_request.created_at}")

    db.close()


if __name__ == "__main__":
    view_data()
