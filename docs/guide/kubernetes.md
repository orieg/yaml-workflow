# Kubernetes Deployment

yaml-workflow provides a Docker image and Helm chart for running workflows on Kubernetes.

## Docker

Run yaml-workflow in a container without installing Python:

```bash
# Run a workflow
docker run --rm -v $(pwd)/workflows:/app/workflows ghcr.io/orieg/yaml-workflow run /app/workflows/hello.yaml

# Start the web dashboard
docker run -p 8080:8080 -v $(pwd)/workflows:/app/workflows ghcr.io/orieg/yaml-workflow

# Validate a workflow
docker run --rm -v $(pwd)/workflows:/app/workflows ghcr.io/orieg/yaml-workflow validate /app/workflows/hello.yaml --format json
```

## Helm Chart

Deploy the web dashboard and run workflows on Kubernetes:

```bash
# Install from the repo
helm install my-workflows ./helm/yaml-workflow

# With inline workflow definitions
helm install my-workflows ./helm/yaml-workflow \
  --set-file workflows.files.pipeline\\.yaml=workflows/pipeline.yaml

# Access the dashboard
kubectl port-forward svc/my-workflows 8080:8080
```

### Configuration

Key values in `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Container image | `ghcr.io/orieg/yaml-workflow` |
| `image.tag` | Image tag | Chart appVersion |
| `serve.port` | Dashboard port | `8080` |
| `workflows.files` | Inline workflow YAML definitions | `{}` |
| `workflows.existingConfigMap` | Use an existing ConfigMap | `""` |
| `runs.persistence.enabled` | Enable PVC for run history | `true` |
| `runs.persistence.size` | Storage size | `1Gi` |
| `ingress.enabled` | Enable Ingress | `false` |
| `cronjob.enabled` | Enable scheduled runs | `false` |
| `cronjob.schedule` | Cron expression | `""` |
| `cronjob.workflow` | Workflow file to run | `""` |

### Inline Workflows

Define workflows directly in `values.yaml`:

```yaml
workflows:
  files:
    data_pipeline.yaml: |
      name: Data Pipeline
      secrets:
        - API_KEY
      steps:
        - name: fetch
          task: http.request
          inputs:
            url: "https://api.example.com/data"
            auth:
              type: bearer
              token_env: API_KEY
        - name: process
          task: python_code
          depends_on: [fetch]
          inputs:
            code: |
              data = steps["fetch"]["result"]["json"]
              result = {"count": len(data)}
```

### Scheduled Runs

Run workflows on a schedule via Kubernetes CronJob:

```yaml
cronjob:
  enabled: true
  schedule: "0 9 * * 1-5"  # Weekdays at 9am
  workflow: "data_pipeline.yaml"
  params: "env=production"
```

## ArgoCD Integration

The Helm chart is GitOps-ready. Point ArgoCD at your repo:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: yaml-workflow
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/your-repo
    path: helm/yaml-workflow
    targetRevision: main
    helm:
      valueFiles:
        - values-production.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: workflows
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

Workflow YAML changes committed to Git are automatically synced to the cluster.

## Argo Workflows Integration

Use yaml-workflow as a step inside Argo Workflows:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: yaml-workflow-step
spec:
  templates:
    - name: run-pipeline
      container:
        image: ghcr.io/orieg/yaml-workflow:latest
        command: ["yaml-workflow", "run"]
        args:
          - /app/workflows/pipeline.yaml
          - --format
          - json
          - "env=production"
        volumeMounts:
          - name: workflows
            mountPath: /app/workflows
```
