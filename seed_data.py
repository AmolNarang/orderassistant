# seed_data.py
from app.database import SessionLocal, init_db, Customer, Product, Order, OrderItem
from datetime import datetime, timedelta


def seed_database():
    """Populate database with sample data"""

    # Initialize database
    init_db()

    db = SessionLocal()

    # Clear existing data
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.query(Product).delete()
    db.query(Customer).delete()

    # Create customers
    customers = [
        Customer(name="John Doe", email="john@example.com", phone="555-0001"),
        Customer(name="Jane Smith", email="jane@example.com", phone="555-0002"),
        Customer(name="Bob Wilson", email="bob@example.com", phone="555-0003"),
    ]
    db.add_all(customers)
    db.commit()

    # Create products
    products = [
        Product(sku="SKU001", name="Wireless Headphones", price=49.99),
        Product(sku="SKU002", name="USB-C Cable", price=15.99),
        Product(sku="SKU003", name="Phone Case", price=25.00),
        Product(sku="SKU004", name="Screen Protector", price=12.99),
        Product(sku="SKU005", name="Bluetooth Speaker", price=79.99),
    ]
    db.add_all(products)
    db.commit()

    # Create orders
    order1 = Order(
        id="ORD001",
        customer_id=customers[0].id,
        total=49.99,
        status="delivered",
        order_date=datetime.utcnow() - timedelta(days=10)
    )
    db.add(order1)
    db.add(OrderItem(order_id="ORD001", product_id=products[0].id, quantity=1))

    order2 = Order(
        id="ORD002",
        customer_id=customers[1].id,
        total=28.98,
        status="shipped",
        order_date=datetime.utcnow() - timedelta(days=3)
    )
    db.add(order2)
    db.add(OrderItem(order_id="ORD002", product_id=products[1].id, quantity=1))
    db.add(OrderItem(order_id="ORD002", product_id=products[3].id, quantity=1))

    order3 = Order(
        id="ORD003",
        customer_id=customers[2].id,
        total=104.99,
        status="pending",
        order_date=datetime.utcnow() - timedelta(days=1)
    )
    db.add(order3)
    db.add(OrderItem(order_id="ORD003", product_id=products[2].id, quantity=1))
    db.add(OrderItem(order_id="ORD003", product_id=products[4].id, quantity=1))

    db.commit()
    db.close()

    print("✅ Database seeded with sample data!")
    print("\n📧 Test emails you can use:")
    print("  - john@example.com (Order: ORD001)")
    print("  - jane@example.com (Order: ORD002)")
    print("  - bob@example.com (Order: ORD003)")


if __name__ == "__main__":
    seed_database()