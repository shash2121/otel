# OpenTelemetry on AWS EKS

Setup guide for the OpenTelemetry (OTel) observability stack on AWS EKS, including the sample app, dashboards, and teardown instructions.

## What This Repository Provisions

| Component | Purpose |
|-----------|---------|
| VPC | 2-AZ network with public/private subnets, NAT, IGW |
| EKS Cluster | Kubernetes 1.31 + managed node group (t3.medium) |
| OpenTelemetry Collector | Receives OTLP (traces + metrics + logs), exports to backends |
| Jaeger | Trace storage + UI (in-memory) |
| Prometheus | Scrapes the OTel Collector's metrics exporter |
| Loki | Log aggregation, stores app logs (in-memory) |
| Grafana | Dashboards (pre-wired with Prometheus, Jaeger, + Loki datasources) |

No RDS, SQS, ALB, Secrets Manager or Pod Identity are needed — the OTel stack runs entirely inside the cluster.

---

## Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform >= 1.0
- `kubectl`
- Docker (for building the sample app images)
- A Docker Hub account (or any registry)

---

## Step 1: Deploy Infrastructure

```bash
# Review / edit terraform.tfvars (region, cluster_name, etc.)
terraform init
terraform apply -auto-approve
```

This takes ~12-15 minutes. Once done, configure kubectl:

```bash
aws eks update-kubeconfig --region us-east-1 --name otel-eks
kubectl get pods
```

You should see pods for `otel-collector`, `jaeger`, `loki`, `prometheus-server`, and `grafana`.

---

## Step 2: Build & Push the Sample App Images

```bash
export DOCKER_REGISTRY=docker.io/<your-username>

docker build -t $DOCKER_REGISTRY/service-a:latest otel-app/service-a/
docker build -t $DOCKER_REGISTRY/service-b:latest otel-app/service-b/

docker push $DOCKER_REGISTRY/service-a:latest
docker push $DOCKER_REGISTRY/service-b:latest
```

> Use a single-architecture build if your cluster nodes are amd64: `docker buildx build --platform linux/amd64 ...`

Update the image references in `k8s/01-service-a.yaml` and `k8s/02-service-b.yaml`:

```yaml
image: docker.io/<your-username>/service-a:latest
image: docker.io/<your-username>/service-b:latest
```

---

## Step 3: Deploy the Sample App

```bash
kubectl apply -k k8s/

kubectl get pods -l app=service-a
kubectl get pods -l app=service-b
```

Both services auto-instrument Flask and the `requests` library via the
`opentelemetry-instrument` wrapper — no manual spans are needed.

---

## Step 4: Generate Traffic

### Quick smoke test (curl)

```bash
kubectl port-forward svc/service-a 5001:5000

curl http://localhost:5001/products
curl -X POST http://localhost:5001/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": 3, "quantity": 2}'
```

### Production-grade load (k6)

The repository includes a `k6-load.js` script that simulates realistic traffic —
concurrent users browsing products, placing orders, and hitting various endpoints.
It ramps from 5 → 20 req/s and back down over 3 minutes.

```bash
brew install k6        # or: apt install k6

kubectl port-forward svc/service-a 5001:5000

k6 run k6-load.js
```

What this gives you:

| Signal | What you'll see |
|--------|----------------|
| **Traces** | Distributed traces spanning Service A → Service B, with visible timing per span |
| **Metrics** | p50/p95/p99 latency, request rate over time, error rate |
| **Logs** | Structured log lines for every request, queryable in Loki via LogQL |

Rerun `k6` a few times while watching Grafana to see the dashboards populate in real time.

---

## Step 5: Open the Dashboards

### Grafana (metrics, traces & logs)

```bash
kubectl port-forward svc/grafana 3000:80
```

- URL: http://localhost:3000
- Username: `admin`
- Password: `otel-demo-admin` (or retrieve it via:)
  ```bash
  kubectl get secret grafana -o jsonpath='{.data.admin-password}' | base64 -d
  ```

Pre-configured datasources: **Prometheus** (default), **Jaeger**, and **Loki**.

### Jaeger UI (traces only)

```bash
kubectl port-forward svc/jaeger-query 16686:16686
```

URL: http://localhost:16686 — search by service `service-a` or `service-b`.

### Viewing Logs in Grafana

App logs flow through the OTel Collector's logs pipeline into Loki. To query them:

1. Open Grafana → **Explore** → select **Loki** as the datasource.
2. Enter a LogQL query:

```logql
{service_name="service-a"} |= "Fetching products"
```

This shows all log entries from Service A that contain "Fetching products". Grafana displays them in a log panel with timestamps, and you can expand each entry to see the full log line with structured attributes.

---

## Step 6: Useful PromQL Examples (in Grafana Explore)

```promql
# Request rate, Service A
rate(http_server_duration_seconds_count{service_name="service-a"}[1m])

# p99 latency, Service B
histogram_quantile(0.99,
  sum by (le) (rate(http_server_duration_seconds_bucket{service_name="service-b"}[1m]))
)

# Error rate
sum(rate(http_server_duration_seconds_count{http_status_code=~"5.."}[1m]))
  / sum(rate(http_server_duration_seconds_count[1m]))
```

---

## Destroying Only the OTel Components

Sometimes you'll want to remove the observability stack *without* destroying the
EKS cluster (e.g. to test a fresh install, or to save cost on Helm releases).

There are two ways:

### Option A: Flip the toggle and apply (recommended)

```bash
# in terraform.tfvars
deploy_observability = false
```

```bash
terraform apply -auto-approve
```

This destroys only the five Helm releases
(`otel-collector`, `jaeger`, `loki`, `prometheus`, `grafana`) and leaves the EKS cluster
and node group untouched.

To bring the stack back, set `deploy_observability = true` and apply again.

### Option B: Targeted destroy (one-off)

```bash
terraform destroy \
  -target='module.eks.helm_release.otel_collector[0]' \
  -target='module.eks.helm_release.jaeger[0]' \
  -target='module.eks.helm_release.loki[0]' \
  -target='module.eks.helm_release.prometheus[0]' \
  -target='module.eks.helm_release.grafana[0]'
```

> After a targeted destroy, the resources still exist in Terraform state as
> "pending deletion". Run `terraform apply` afterwards to reconcile, or set
> `deploy_observability = false` to make the change permanent.

---

## Full Cleanup

```bash
# Remove app
kubectl delete -k k8s/

# Destroy everything (cluster + VPC + observability)
terraform destroy -auto-approve
```

---

## IAM Permissions Required

The Terraform AWS provider needs rights to create:

- VPC, subnets, IGW, NAT gateway, route tables
- EKS cluster + node group
- IAM roles and policy attachments (cluster + node group)

No extra IAM is required for the OTel stack itself — the OTel Collector, Jaeger,
Loki, Prometheus and Grafana run entirely in-cluster and do not call AWS APIs.

---

## Troubleshooting

### `'image.repository' must be set` error on `terraform apply`

This happens with newer versions of the `opentelemetry-collector` chart. The fix
is already applied in `modules/eks/observability.tf` — we pin
`image.repository = otel/opentelemetry-collector-contrib` and
`image.tag = 0.110.0` so a default image is always present.

### Logs not appearing in Loki / Grafana

- Verify Loki is running: `kubectl get pods -l app.kubernetes.io/name=loki`
- Check the OTel Collector logs for Loki exporter errors:
  ```bash
  kubectl logs deploy/otel-collector | grep loki
  ```
- Send some traffic to the sample app first — logs are only generated when
  endpoints are hit (the `logger.info()` calls in the app code).
- If Loki shows `TOO_MANY_REQUESTS`, increase `ingestion_rate_mb` in the Loki Helm values.

### OTel Collector pod in `CrashLoopBackOff`

```bash
kubectl logs deploy/otel-collector
```

Most often this is a YAML config issue or a backend being unreachable. Confirm
Jaeger and Loki services are running:

```bash
kubectl get svc jaeger-collector loki
```

The OTel Collector depends on both being reachable; Helm applies them in the
right order but backends can take 30-60 seconds to become ready.

### Prometheus shows no metrics

- Verify the OTel collector is up: `kubectl get pods -l app.kubernetes.io/name=opentelemetry-collector`
- Check Prometheus targets: `kubectl port-forward svc/prometheus-server 9090:80` → http://localhost:9090/targets
- Send some traffic to the sample app first — auto-instrumented metrics only
  appear once requests hit the services.

### Grafana datasources not visible

- `kubectl get configmap` should include a `grafana` ConfigMap with the
  datasources.
- If you set a custom release name, update the `prometheus-server` /
  `jaeger-query` / `loki` service URLs in `modules/eks/observability.tf`.

---

## File Structure

```
otel/
├── terraform.tf            # Terraform + S3 backend
├── providers.tf
├── variables.tf
├── locals.tf
├── main.tf                 # VPC + EKS modules
├── outputs.tf
├── terraform.tfvars        # Edit cluster name, region, etc.
├── modules/
│   ├── vpc/                # VPC with public/private subnets (2 AZs)
│   └── eks/                # EKS cluster + node group + helm releases
│       ├── main.tf
│       ├── providers.tf
│       ├── observability.tf
│       ├── variables.tf
│       └── outputs.tf
├── otel-app/               # Sample app (two Flask services)
│   ├── service-a/
│   ├── service-b/
│   ├── docker-compose.yaml
│   ├── collector-config.yaml
│   └── build-and-push.sh
├── k8s/                    # Deployment manifests for the sample app
├── k6-load.js              # Load-test script (production-like traffic)
└── blog.md                 # Long-form Medium article
```