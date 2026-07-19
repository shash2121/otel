import time
import random
import logging

from flask import Flask, jsonify, request

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service-b")

PRODUCTS = [
    {"id": 1, "name": "Wireless Mouse", "price": 29.99, "stock": 150},
    {"id": 2, "name": "Mechanical Keyboard", "price": 89.99, "stock": 75},
    {"id": 3, "name": "USB-C Hub", "price": 45.00, "stock": 200},
    {"id": 4, "name": "27-inch Monitor", "price": 299.99, "stock": 30},
    {"id": 5, "name": "Noise Cancelling Headphones", "price": 179.99, "stock": 60},
    {"id": 6, "name": "Webcam 1080p", "price": 59.99, "stock": 120},
    {"id": 7, "name": "Laptop Stand", "price": 39.99, "stock": 90},
    {"id": 8, "name": "Desk Lamp LED", "price": 24.99, "stock": 180},
]

orders_db = []


@app.route("/products")
def get_products():
    delay = random.uniform(0.05, 0.5)
    time.sleep(delay)
    logger.info(f"Returning {len(PRODUCTS)} products (took {delay:.3f}s)")
    return jsonify({"products": PRODUCTS, "count": len(PRODUCTS)})


@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        logger.warning(f"Product not found: {product_id}")
        return jsonify({"error": "product not found"}), 404

    delay = random.uniform(0.1, 0.8)
    time.sleep(delay)

    order = {
        "id": len(orders_db) + 1,
        "product": product["name"],
        "quantity": quantity,
        "total": round(product["price"] * quantity, 2),
        "status": "created",
    }
    orders_db.append(order)
    logger.info(f"Order created: {order}")
    return jsonify(order), 201


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
