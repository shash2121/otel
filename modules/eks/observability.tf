resource "helm_release" "otel_collector" {
  count      = var.deploy_observability ? 1 : 0
  name       = "otel-collector"
  repository = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart      = "opentelemetry-collector"
  namespace  = "default"

  values = [
    yamlencode({
      mode = "deployment"

      # Required by the chart: must specify image repository explicitly
      image = {
        repository = "otel/opentelemetry-collector-contrib"
        tag        = "0.110.0"
        pullPolicy = "IfNotPresent"
      }

      config = {
        receivers = {
          otlp = {
            protocols = {
              grpc = { endpoint = "0.0.0.0:4317" }
              http = { endpoint = "0.0.0.0:4318" }
            }
          }
        }
        processors = {
          batch = {}
          memory_limiter = {
            check_interval         = "1s"
            limit_percentage       = 80
            spike_limit_percentage = 25
          }
        }
        exporters = {
          jaeger = {
            endpoint = "jaeger-collector.default.svc.cluster.local:14250"
            tls = { insecure = true }
          }
          prometheus = {
            endpoint = "0.0.0.0:8889"
          }
          loki = {
            endpoint = "http://loki.default.svc.cluster.local:3100/loki/api/v1/push"
            tls = { insecure = true }
          }
        }
        service = {
          pipelines = {
            traces = {
              receivers  = ["otlp"]
              processors = ["memory_limiter", "batch"]
              exporters  = ["jaeger"]
            }
            metrics = {
              receivers  = ["otlp"]
              processors = ["memory_limiter", "batch"]
              exporters  = ["prometheus"]
            }
            logs = {
              receivers  = ["otlp"]
              processors = ["memory_limiter", "batch"]
              exporters  = ["loki"]
            }
          }
        }
      }
      resources = {
        limits = {
          cpu    = "500m"
          memory = "512Mi"
        }
        requests = {
          cpu    = "250m"
          memory = "256Mi"
        }
      }
    })
  ]

  set {
    name  = "podAnnotations.prometheus\\.io/scrape"
    value = "true"
  }
  set {
    name  = "podAnnotations.prometheus\\.io/port"
    value = "8889"
  }

  depends_on = [aws_eks_node_group.node_group]
}

resource "helm_release" "jaeger" {
  count      = var.deploy_observability ? 1 : 0
  name       = "jaeger"
  repository = "https://jaegertracing.github.io/helm-charts"
  chart      = "jaeger"
  namespace  = "default"

  set {
    name  = "provisionDataStore.cassandra"
    value = "false"
  }
  set {
    name  = "allInOne.enabled"
    value = "true"
  }
  set {
    name  = "storage.type"
    value = "memory"
  }

  depends_on = [aws_eks_node_group.node_group]
}

resource "helm_release" "prometheus" {
  count      = var.deploy_observability ? 1 : 0
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus"
  namespace  = "default"

  set {
    name  = "alertmanager.enabled"
    value = "false"
  }
  set {
    name  = "kube-state-metrics.enabled"
    value = "false"
  }
  set {
    name  = "prometheus-node-exporter.enabled"
    value = "false"
  }
  set {
    name  = "prometheus-pushgateway.enabled"
    value = "false"
  }
  set {
    name  = "server.persistentVolume.enabled"
    value = "false"
  }

  values = [
    yamlencode({
      extraScrapeConfigs = <<-EOT
        - job_name: 'otel-collector'
          scrape_interval: 10s
          static_configs:
            - targets: ['otel-collector.default.svc.cluster.local:8889']
      EOT
    })
  ]

  depends_on = [helm_release.otel_collector]
}

resource "helm_release" "loki" {
  count      = var.deploy_observability ? 1 : 0
  name       = "loki"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  namespace  = "default"

  set {
    name  = "deploymentMode"
    value = "SingleBinary"
  }
  set {
    name  = "loki.auth_enabled"
    value = "false"
  }
  set {
    name  = "loki.commonConfig.replication_factor"
    value = "1"
  }
  set {
    name  = "persistence.enabled"
    value = "false"
  }

  depends_on = [aws_eks_node_group.node_group]
}

resource "helm_release" "grafana" {
  count      = var.deploy_observability ? 1 : 0
  name       = "grafana"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "grafana"
  namespace  = "default"

  set {
    name  = "adminUser"
    value = "admin"
  }
  set {
    name  = "adminPassword"
    value = "otel-demo-admin"
  }
  set {
    name  = "persistence.enabled"
    value = "false"
  }

  values = [
    yamlencode({
      datasources = {
        "datasources.yaml" = {
          apiVersion = 1
          datasources = [
            {
              name      = "Prometheus"
              type      = "prometheus"
              url       = "http://prometheus-server.default.svc.cluster.local"
              access    = "proxy"
              isDefault = true
            },
            {
              name   = "Jaeger"
              type   = "jaeger"
              url    = "http://jaeger-query.default.svc.cluster.local:16686"
              access = "proxy"
            },
            {
              name   = "Loki"
              type   = "loki"
              url    = "http://loki.default.svc.cluster.local:3100"
              access = "proxy"
            }
          ]
        }
      }
    })
  ]

  depends_on = [helm_release.prometheus, helm_release.jaeger, helm_release.loki]
}
