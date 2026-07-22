import time
import random
import logging
import os

from flask import Flask, jsonify, request, g

from opentelemetry import trace, metrics, _logs
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "service-b")
resource = Resource.create({"service.name": SERVICE_NAME})

trace.set_tracer_provider(TracerProvider(resource=resource))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

reader = PeriodicExportingMetricReader(OTLPMetricExporter())
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
meter = metrics.get_meter(__name__)

_logs.set_logger_provider(LoggerProvider(resource=resource))
_logs.get_logger_provider().add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
handler = LoggingHandler()
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

FlaskInstrumentor().instrument()

app = Flask(__name__)

logger = logging.getLogger("service-b")

http_duration = meter.create_histogram(
    "http.server.request.duration",
    unit="s",
    description="Duration of HTTP requests"
)

@app.before_request
def _start_timer():
    g._start = time.time()

@app.after_request
def _record_duration(response):
    if hasattr(g, "_start"):
        http_duration.record(
            time.time() - g._start,
            attributes={
                "http.method": request.method,
                "http.route": request.path,
                "http.status_code": response.status_code,
                "http.scheme": request.scheme,
            }
        )
    return response

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
