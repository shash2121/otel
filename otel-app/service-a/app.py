import time
import random
import logging
import os

import requests
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
from opentelemetry.instrumentation.requests import RequestsInstrumentor

SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "service-a")
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
RequestsInstrumentor().instrument()

app = Flask(__name__)

logger = logging.getLogger("service-a")
SERVICE_B_URL = os.environ.get("SERVICE_B_URL", "http://service-b:5000")

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


@app.route("/")
def home():
    logger.info("Home endpoint called")
    return jsonify({
        "service": "service-a",
        "message": "OpenTelemetry Demo - API Gateway",
        "endpoints": ["/", "/products", "/orders", "/health", "/products/search?q=..."]
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
    return jsonify({"status": "healthy"})


@app.route("/products/search")
def search_products():
    q = request.args.get("q", "")
    logger.info(f"Searching products with query: {q}")
    try:
        resp = requests.get(f"{SERVICE_B_URL}/products/search?q={q}", timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        logger.error(f"Search failed: {e}")
        return jsonify({"error": "service-b unavailable"}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
