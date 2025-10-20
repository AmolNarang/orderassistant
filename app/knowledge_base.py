# app/knowledge_base.py

from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain.embeddings import HuggingFaceEmbeddings

from config import API_KEY

# Sample knowledge base content
COMPANY_POLICIES = """
RETURN POLICY:
- Customers can return items within 30 days of delivery
- Items must be unused and in original packaging
- Refunds processed within 5-7 business days
- Original shipping costs are non-refundable
- Electronics have a 14-day return window
- Custom or personalized items cannot be returned

SHIPPING POLICY:
- Standard shipping: 5-7 business days
- Express shipping: 2-3 business days
- Free shipping on orders over $50
- We ship Monday-Friday
- Tracking numbers provided within 24 hours of shipment

REFUND POLICY:
- Refunds issued to original payment method
- Processing time: 5-7 business days after we receive the item
- Shipping costs are non-refundable unless item was defective
- Partial refunds may apply if item shows signs of use

WARRANTY INFORMATION:
- 1-year manufacturer warranty on electronics
- 90-day warranty on accessories
- Warranty covers manufacturing defects only
- Does not cover accidental damage or misuse

EXCHANGE POLICY:
- Free exchanges for defective items
- Size/color exchanges subject to availability
- Exchange shipping is free for defective items
- Customer pays return shipping for non-defective exchanges
"""

FAQS = """
Q: How long does shipping take?
A: Standard shipping takes 5-7 business days. Express shipping is 2-3 business days.

Q: Can I cancel my order?
A: Yes, if the order hasn't shipped yet. Contact us immediately with your order number.

Q: What if my item arrives damaged?
A: Contact us within 48 hours with photos. We'll send a replacement or full refund immediately.

Q: How do I track my order?
A: You'll receive a tracking number via email within 24 hours of shipment.

Q: Do you ship internationally?
A: Currently we only ship within the United States.

Q: What payment methods do you accept?
A: We accept all major credit cards, PayPal, and Apple Pay.

Q: Can I change my shipping address?
A: Only if the order hasn't shipped yet. Contact us ASAP with your order number.

Q: What if I received the wrong item?
A: We'll send the correct item immediately and provide a free return label.
"""

PRODUCT_INFO = """
WIRELESS HEADPHONES (SKU001):
- Bluetooth 5.0 connectivity
- 20-hour battery life
- Noise cancellation feature
- Compatible with all devices
- Comes with charging cable and carrying case
- 1-year warranty

USB-C CABLE (SKU002):
- 6 feet long
- Fast charging compatible
- Data transfer speed: 480 Mbps
- Durable braided design
- Works with all USB-C devices

PHONE CASE (SKU003):
- Shockproof design
- Raised edges for screen protection
- Wireless charging compatible
- Available in multiple colors
- Slim profile

SCREEN PROTECTOR (SKU004):
- Tempered glass
- 9H hardness
- Bubble-free installation
- Case-friendly design
- Includes installation kit

BLUETOOTH SPEAKER (SKU005):
- 360-degree sound
- Waterproof (IPX7 rating)
- 12-hour battery life
- Built-in microphone
- Pairs with multiple devices
"""


def create_knowledge_base():
    """Create and return a vector store with company knowledge"""

    # Create documents
    documents = [
        Document(page_content=COMPANY_POLICIES, metadata={"source": "policies", "type": "policy"}),
        Document(page_content=FAQS, metadata={"source": "faqs", "type": "faq"}),
        Document(page_content=PRODUCT_INFO, metadata={"source": "products", "type": "product_info"})
    ]

    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )

    splits = text_splitter.split_documents(documents)

    # ✅ Use HuggingFace embeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    # Create vector store
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )

    print(f"✅ Knowledge base created with {len(splits)} chunks")

    return vectorstore


def get_knowledge_base():
    """Get or create knowledge base"""
    import os

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    if os.path.exists("./chroma_db"):
        # Load existing
        vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=embeddings
        )
    else:
        # Create new
        vectorstore = create_knowledge_base()

    return vectorstore