import time
import random
import logging
import os

from flask import Flask, jsonify, request, g
from sqlalchemy import create_engine, text, Table, Column, Integer, String, Float, MetaData
from sqlalchemy.exc import OperationalError
import boto3
import json

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
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

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
    "http.server.request.duration", unit="s", description="Duration of HTTP requests"
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
            },
        )
    return response

# ==== RDS discovery via Pod Identity ====
DB_IDENTIFIER = os.environ.get("DB_IDENTIFIER", "otel-demo-db")
SECRET_NAME   = os.environ.get("SECRET_NAME", "otel-demo-rds-credentials")
AWS_REGION    = os.environ.get("AWS_REGION", "us-east-1")

def _get_db_credentials():
    secrets = boto3.client("secretsmanager", region_name=AWS_REGION)
    resp = secrets.get_secret_value(SecretId=SECRET_NAME)
    creds = json.loads(resp["SecretString"])
    return creds["DB_USERNAME"], creds["DB_PASSWORD"], creds.get("DB_HOST", "")

def _get_rds_endpoint():
    try:
        rds = boto3.client("rds", region_name=AWS_REGION)
        inst = rds.describe_db_instances(DBInstanceIdentifier=DB_IDENTIFIER)
        ep = inst["DBInstances"][0]["Endpoint"]
        return ep["Address"], ep["Port"]
    except Exception as e:
        logger.warning(f"RDS discovery failed, using env vars: {e}")
        return os.environ.get("DB_HOST", "localhost"), int(os.environ.get("DB_PORT", 5432))

DB_HOST, DB_PORT = _get_rds_endpoint()
DB_USER, DB_PASS, _ = _get_db_credentials()
DB_NAME = os.environ.get("DB_NAME", "otel_demo")

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_size=10,
    max_overflow=0,
)
SQLAlchemyInstrumentor().instrument(engine=engine)

def _init_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    stock INT DEFAULT 0
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    product_name VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'created'
                )
            """))
            result = conn.execute(text("SELECT COUNT(*) FROM products"))
            if result.scalar() == 0:
                conn.execute(text("""
                    INSERT INTO products (name, price, stock) VALUES
                    ('Wireless Mouse', 29.99, 150),
                    ('Mechanical Keyboard', 89.99, 75),
                    ('USB-C Hub', 45.00, 200),
                    ('27-inch Monitor', 299.99, 30),
                    ('Noise Cancelling Headphones', 179.99, 60),
                    ('Webcam 1080p', 59.99, 120),
                    ('Laptop Stand', 39.99, 90),
                    ('Desk Lamp LED', 24.99, 180)
                """))
            conn.commit()
        logger.info("Database initialized")
    except OperationalError as e:
        logger.error(f"DB init failed: {e}")


@app.route("/products")
def get_products():
    delay = random.uniform(0.05, 0.5)
    time.sleep(delay)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, name, price, stock FROM products ORDER BY id"))
        products = [{"id": r[0], "name": r[1], "price": float(r[2]), "stock": r[3]} for r in rows]
    logger.info(f"Returning {len(products)} products (took {delay:.3f}s)")
    return jsonify({"products": products, "count": len(products)})


@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    delay = random.uniform(0.1, 0.8)
    time.sleep(delay)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT name, price FROM products WHERE id = :pid"),
            {"pid": product_id}
        ).first()

        if not row:
            logger.warning(f"Product not found: {product_id}")
            return jsonify({"error": "product not found"}), 404

        total = round(float(row[1]) * quantity, 2)
        conn.execute(
            text("INSERT INTO orders (product_name, quantity, total) VALUES (:name, :qty, :total)"),
            {"name": row[0], "qty": quantity, "total": total}
        )
        conn.commit()

    order = {"product": row[0], "quantity": quantity, "total": total, "status": "created"}
    logger.info(f"Order created: {order}")
    return jsonify(order), 201


@app.route("/products/search")
def search_products():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    delay = random.uniform(0.05, 0.3)
    time.sleep(delay)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, name, price, stock FROM products WHERE name ILIKE :q ORDER BY id"),
            {"q": f"%{q}%"}
        )
        products = [{"id": r[0], "name": r[1], "price": float(r[2]), "stock": r[3]} for r in rows]
    logger.info(f"Search '{q}' returned {len(products)} results (took {delay:.3f}s)")
    return jsonify({"products": products, "count": len(products), "query": q})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    _init_db()
    app.run(host="0.0.0.0", port=5000)
