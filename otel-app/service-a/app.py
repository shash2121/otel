import time
import random
import logging
import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service-a")

SERVICE_B_URL = os.environ.get("SERVICE_B_URL", "http://service-b:5000")


@app.route("/")
def home():
    logger.info("Home endpoint called")
    return jsonify({
        "service": "service-a",
        "message": "OpenTelemetry Demo - API Gateway",
        "endpoints": ["/", "/products", "/orders", "/health", "/chuck"]
    })


@app.route("/products")
def products():
    logger.info("Fetching products from service-b")
    try:
        resp = requests.get(f"{SERVICE_B_URL}/products", timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        logger.error(f"Failed to reach service-b: {e}")
        return jsonify({"error": "service-b unavailable"}), 503


@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    logger.info(f"Creating order: {data}")
    try:
        resp = requests.post(f"{SERVICE_B_URL}/orders", json=data, timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json()), 201
    except requests.RequestException as e:
        logger.error(f"Failed to create order: {e}")
        return jsonify({"error": "service-b unavailable"}), 503


@app.route("/health")
def health():
    logger.info("Health check")
    return jsonify({"status": "healthy"})


@app.route("/chuck")
def chuck():
    logger.info("Chuck Norris fact requested")
    time.sleep(random.uniform(0.05, 0.3))
    facts = [
        "Chuck Norris can query a database by staring at the monitor.",
        "Chuck Norris's code has no bugs. It's just undocumented features.",
        "Chuck Norris does not need a debugger. He fixes code by looking at it.",
        "When Chuck Norris deploys, CI/CD skips the tests. The tests are scared.",
        "Chuck Norris can close a connection pool just by thinking about it.",
        "Chuck Norris writes code that optimizes itself out of respect.",
    ]
    fact = random.choice(facts)
    logger.info(f"Returning fact: {fact}")
    return jsonify({"fact": fact})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
