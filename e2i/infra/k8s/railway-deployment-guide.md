# Railway Kubernetes Deployment Guide

This guide explains how to deploy your Datawarehouse application to Railway using the Kubernetes manifests.

## Prerequisites

1. Railway account with Kubernetes support
2. `kubectl` configured to connect to your Railway cluster
3. `kustomize` installed locally
4. Docker images built and pushed to a registry accessible by Railway

## Project Structure

```
e2i/infra/k8s/
├── base/                           # Base Kubernetes manifests
│   ├── namespace.yaml             # Namespace configuration
│   ├── configmaps.yaml            # Environment variables and config
│   ├── configmaps-additional.yaml # Additional config maps
│   ├── secrets.yaml               # Sensitive data (passwords, API keys)
│   ├── persistent-volumes.yaml    # Storage claims
│   ├── databases.yaml             # PostgreSQL databases
│   ├── core-services.yaml         # Redis, ClickHouse, MinIO
│   ├── tokenization.yaml          # Tokenization service
│   ├── airflow.yaml               # Airflow components
│   ├── backend.yaml               # Django and Orchestrator services
│   ├── frontend.yaml              # Frontend and Metabase
│   ├── ingress.yaml               # External access configuration
│   └── kustomization.yaml         # Kustomize base configuration
├── railway.yaml                   # Railway-specific kustomization
├── railway-patches.yaml           # Railway-specific patches
└── railway-deployment-guide.md    # This file
```

## Railway-Specific Configuration

### 1. Update Docker Image References

In `railway-patches.yaml`, update the image references to match your Railway registry:

```yaml
# Replace these with your actual Railway image references
image: railway.dockerfile/orchestrator:latest
image: railway.dockerfile/django:latest
image: railway.dockerfile/tokenization-service:latest
image: railway.dockerfile/frontend:latest
```

### 2. Configure Secrets

Update the secrets in `base/secrets.yaml` with your actual base64-encoded values:

```bash
# Example: Generate base64 for a password
echo -n "your-password" | base64
```

### 3. Update Domain Configuration

In `base/ingress.yaml`, replace `your-domain.com` with your actual Railway domain.

### 4. Storage Configuration

Railway may use different storage classes. Update `base/persistent-volumes.yaml` if needed:

```yaml
storageClassName: railway-storage  # Update if Railway uses different storage class
```

## Deployment Steps

### 1. Build and Push Docker Images

Ensure all your Docker images are built and pushed to a registry accessible by Railway:

```bash
# Build images (adjust paths as needed)
docker build -t your-registry/e2i-orchestrator:latest ./e2i/orchestrator
docker build -t your-registry/e2i-django:latest ./e2i/backend
docker build -t your-registry/tokenization-service:latest ./tokenization-service
docker build -t your-registry/e2i-frontend:latest ./e2i/frontend

# Push to registry
docker push your-registry/e2i-orchestrator:latest
docker push your-registry/e2i-django:latest
docker push your-registry/tokenization-service:latest
docker push your-registry/e2i-frontend:latest
```

### 2. Update Image References

Update the image references in `railway-patches.yaml` to match your registry.

### 3. Deploy to Railway

```bash
# Navigate to the k8s directory
cd e2i/infra/k8s

# Apply the Railway configuration
kustomize build railway | kubectl apply -f -

# Monitor the deployment
kubectl get pods -n datawarehouse -w
```

### 4. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n datawarehouse

# Check services
kubectl get services -n datawarehouse

# Check ingress
kubectl get ingress -n datawarehouse
```

## Railway-Specific Considerations

### 1. Resource Limits

Railway may have resource limits. Consider adding resource requests and limits to your deployments:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 2. Health Checks

Ensure all your applications have proper health check endpoints:

- Django: `/health`
- Orchestrator: `/health`
- Tokenization: `/api/v1/health`
- Frontend: `/`
- Airflow: `/health`

### 3. Environment Variables

Railway may provide environment variables differently. Consider using Railway's environment variable injection:

```yaml
env:
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: railway-secrets
      key: DATABASE_URL
```

### 4. Storage

Railway's storage may be ephemeral. Consider using Railway's managed databases instead of self-hosted PostgreSQL instances.

## Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**: Check logs with `kubectl logs <pod-name> -n datawarehouse`
2. **ImagePullBackOff**: Verify image references and registry access
3. **PersistentVolumeClaim Pending**: Check storage class availability
4. **Service Unreachable**: Verify service selectors and port configurations

### Useful Commands

```bash
# Check pod logs
kubectl logs -f deployment/django -n datawarehouse

# Describe pod for events
kubectl describe pod <pod-name> -n datawarehouse

# Port forward for testing
kubectl port-forward service/frontend 8080:80 -n datawarehouse

# Check resource usage
kubectl top pods -n datawarehouse
```

## Security Considerations

1. **Secrets Management**: Use Railway's secret management instead of hardcoded secrets
2. **Network Policies**: Consider implementing network policies for service isolation
3. **RBAC**: Set up proper role-based access control
4. **SSL/TLS**: Configure proper SSL certificates for production

## Monitoring and Logging

Consider integrating with Railway's monitoring and logging solutions:

1. Set up health check endpoints
2. Configure proper logging levels
3. Implement metrics collection
4. Set up alerting for critical services

## Scaling Considerations

For production deployments:

1. Set appropriate replica counts
2. Configure horizontal pod autoscaling
3. Implement proper load balancing
4. Consider database connection pooling
