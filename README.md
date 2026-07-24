# OpenTelemetry on AWS EKS

Terraform code to provision the **EKS infrastructure** (VPC + EKS cluster), plus
a sample app and Helm values files for manually setting up the OpenTelemetry
observability stack.

## What Terraform Provisions

| Component | Purpose |
|-----------|---------|
| VPC | 2-AZ network with public/private subnets, NAT, IGW |
| EKS Cluster | Kubernetes 1.31 + managed node group (t3.medium) |
| EBS CSI Driver | EKS addon — provisions gp2 volumes for PVCs |
| RDS PostgreSQL | db.t3.micro, 20GB, private subnets |
| Secrets Manager | Stores DB credentials (auto-generated password) |
| Pod Identity | Maps `otel-demo-sa` → IAM role for RDS + Secrets access |
| IAM Roles | Cluster, node group, EBS CSI, and pod identity roles |

Everything else — OpenTelemetry Collector, Jaeger, Loki, Prometheus,
Alertmanager, Grafana, and the sample app — is deployed manually via Helm and
kubectl.

---

## Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform >= 1.0.0
- `kubectl`
- `helm` (for the observability stack)
- Docker (for building sample app images)
- `k6` (for load testing)

---

## Step 1: Provision Infrastructure with Terraform

```bash
terraform init
terraform apply -auto-approve
```

This takes ~12–15 minutes (mostly EKS). Once done:

```bash
aws eks update-kubeconfig --region us-east-1 --name otel-eks
kubectl get nodes
```

---

## Step 2: Deploy the Observability Stack (Manual Helm)

The Terraform here only creates the cluster. Deploy OTel and the backends with
Helm commands.

Full steps are in [`blog.md`](blog.md), but the summary is:

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install jaeger jaegertracing/jaeger \
  --set provisionDataStore.cassandra=false \
  --set allInOne.enabled=true \
  --set storage.type=badger \
  --set persistence.enabled=true \
  --set persistence.size=10Gi

helm upgrade --install loki grafana/loki \
  --values helm-values/loki.yaml

helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  --values helm-values/otel-collector.yaml

helm upgrade --install prometheus prometheus-community/prometheus \
  --values helm-values/prometheus.yaml \
  --set alertmanager.enabled=true \
  --set alertmanager.persistentVolume.enabled=true \
  --set alertmanager.persistentVolume.size=2Gi \
  --set kube-state-metrics.enabled=false \
  --set prometheus-node-exporter.enabled=false \
  --set prometheus-pushgateway.enabled=false \
  --set server.persistentVolume.enabled=true \
  --set server.persistentVolume.size=10Gi

helm upgrade --install grafana grafana/grafana \
  --values helm-values/grafana.yaml \
  --set adminUser=admin \
  --set adminPassword=otel-demo-admin \
  --set persistence.enabled=true \
  --set persistence.size=2Gi
```

Grafana datasources (Prometheus, Jaeger, Loki) are pre-configured in
`helm-values/grafana.yaml`.

---

## Step 3: Build & Push the Sample App

```bash
export DOCKER_REGISTRY=docker.io/<your-username>

docker buildx build --platform linux/amd64 \
  -t $DOCKER_REGISTRY/service-a:latest otel-app/service-a/ --push

docker buildx build --platform linux/amd64 \
  -t $DOCKER_REGISTRY/service-b:latest otel-app/service-b/ --push
```

> Pre-built images: `sha2121/service-a:latest` and `sha2121/service-b:latest`.

---

## Step 4: Deploy the Sample App

```bash
kubectl apply -k k8s/

kubectl get pods -l app=service-a
kubectl get pods -l app=service-b
```

---

## Step 5: Generate Traffic

```bash
kubectl port-forward svc/service-a 5001:5000

# Smoke test
curl http://localhost:5001/products
curl -X POST http://localhost:5001/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": 3, "quantity": 2}'

# Production-grade load
k6 run k6-load.js
```

---

## Step 6: Open Dashboards

```bash
kubectl port-forward svc/grafana 3000:80
kubectl port-forward svc/jaeger 16686:16686
kubectl port-forward svc/prometheus-alertmanager 9093:9093
```

- Grafana: http://localhost:3000 (admin / otel-demo-admin)
- Jaeger: http://localhost:16686
- Alertmanager: http://localhost:9093

See `blog.md` for detailed PromQL, LogQL, and alert testing steps.

---

## Cleanup

```bash
# Remove the sample app
kubectl delete -k k8s/

# Uninstall the observability stack
helm uninstall otel-collector jaeger loki prometheus grafana

# Delete PVCs
kubectl delete pvc --all

# Destroy the EKS infrastructure
terraform destroy -auto-approve
```

---

## No IAM Required for OTel

The observability stack runs entirely in-cluster and does not call AWS APIs. Only
the Terraform AWS provider needs permissions to create VPC, EKS, and IAM
resources.

---

## File Structure

```
otel/
├── terraform.tf            # Terraform + version constraint
├── providers.tf            # AWS provider
├── variables.tf            # Input variables
├── locals.tf               # Common tags
├── main.tf                 # VPC + EKS modules
├── outputs.tf              # Cluster info + sample-app port-forward cmds
├── terraform.tfvars        # Your values (edit this!)
├── modules/
│   ├── vpc/                # VPC with public/private subnets (2 AZs)
│   └── eks/                # EKS cluster + node group + IAM
├── helm-values/            # Helm values for observability stack
│   ├── otel-collector.yaml
│   ├── prometheus.yaml
│   ├── loki.yaml
│   └── grafana.yaml
├── otel-app/               # Sample app (two Flask services)
│   ├── service-a/
│   ├── service-b/
│   ├── docker-compose.yaml
│   ├── collector-config.yaml
│   └── build-and-push.sh
├── k8s/                      # Deployment manifests + storage class fix
│   ├── 00-storageclass.yaml
│   ├── 01-service-a.yaml
│   ├── 02-service-b.yaml
│   └── kustomization.yaml
├── k6-load.js                # Load-test script
├── README.md                 # This file
└── blog.md                   # Full manual setup guide
```
