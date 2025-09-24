# Datawarehouse Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Datawarehouse application, optimized for Railway platform deployment.

## Overview

The deployment includes all services from the original Docker Compose setup:

- **Databases**: PostgreSQL instances for Airflow, E2I, Tokenization, and Metabase
- **Core Services**: Redis, ClickHouse, MinIO
- **Application Services**: Airflow (webserver + scheduler), Orchestrator, Django, Reporting, Tokenization Service
- **Frontend Services**: React Frontend, Metabase

## File Structure

```
e2i/infra/k8s/
├── base/                           # Base Kubernetes manifests
│   ├── namespace.yaml             # Namespace configuration
│   ├── configmaps.yaml            # Environment variables and configuration
│   ├── configmaps-additional.yaml # Additional config maps (DAGs, init SQL)
│   ├── secrets.yaml               # Sensitive data (passwords, API keys)
│   ├── persistent-volumes.yaml    # Storage claims for all services
│   ├── databases.yaml             # PostgreSQL deployments and services
│   ├── core-services.yaml         # Redis, ClickHouse, MinIO
│   ├── tokenization.yaml          # Tokenization service
│   ├── airflow.yaml               # Airflow components (init, webserver, scheduler)
│   ├── backend.yaml               # Django, Orchestrator, Reporting services
│   ├── frontend.yaml              # Frontend and Metabase
│   ├── ingress.yaml               # External access configuration
│   └── kustomization.yaml         # Kustomize base configuration
├── railway.yaml                   # Railway-specific kustomization
├── railway-patches.yaml           # Railway-specific image patches
├── railway-deploy.sh              # Railway deployment script
├── railway-deployment-guide.md    # Detailed Railway deployment guide
└── README.md                      # This file
```

## Quick Start

### Prerequisites

1. Railway account with Kubernetes support
2. `kubectl` configured for Railway cluster
3. `kustomize` installed
4. Docker images built and pushed to accessible registry

### Deploy to Railway

```bash
cd e2i/infra/k8s

# Make deployment script executable
chmod +x railway-deploy.sh

# Deploy to Railway
./railway-deploy.sh deploy
```

### Access Services

```bash
# Show access information
./railway-deploy.sh access

# Check status
./railway-deploy.sh status
```

## Key Features

### 1. **Service Dependencies**
- Init containers ensure proper startup order
- Health checks for all services
- Proper service discovery with DNS

### 2. **Data Persistence**
- Persistent volumes for all databases
- Separate storage for MinIO, ClickHouse, Redis
- Export directory for file downloads

### 3. **Security**
- Secrets management for sensitive data
- ConfigMaps for non-sensitive configuration
- Base64 encoded secrets (update with real values)

### 4. **Railway Optimization**
- Railway-specific image references
- Optimized resource allocation
- Proper health check endpoints

### 5. **Monitoring & Debugging**
- Comprehensive logging
- Health check endpoints
- Port-forwarding for local access

## Configuration

### Update Secrets

Before deployment, update the secrets in `base/secrets.yaml`:

```bash
# Generate base64 encoded secrets
echo -n "your-password" | base64

# Update the secrets.yaml file with your actual values
```

### Update Image References

In `railway-patches.yaml`, update image references to match your registry:

```yaml
image: your-registry/e2i-orchestrator:latest
image: your-registry/e2i-django:latest
image: your-registry/tokenization-service:latest
image: your-registry/e2i-frontend:latest
```

### Configure Domain

In `base/ingress.yaml`, replace `your-domain.com` with your actual Railway domain.

## Service Endpoints

| Service | Internal Port | External Access |
|---------|---------------|-----------------|
| Frontend | 80 | `/` |
| Django API | 8001 | `/api/v1` |
| Orchestrator | 8002 | `/orchestrator` |
| Reporting | 8003 | `/reporting` |
| Tokenization | 8004 | `/tokenization` |
| Airflow | 8080 | `/airflow` |
| Metabase | 3000 | `/metabase` |

## Health Checks

All services include health check endpoints:

- Django: `/health`
- Orchestrator: `/health`
- Tokenization: `/api/v1/health`
- Frontend: `/`
- Airflow: `/health`

## Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**
   ```bash
   kubectl logs <pod-name> -n datawarehouse
   kubectl describe pod <pod-name> -n datawarehouse
   ```

2. **ImagePullBackOff**
   - Verify image references in `railway-patches.yaml`
   - Check registry access permissions

3. **PersistentVolumeClaim Pending**
   - Verify storage class availability
   - Check storage quotas

4. **Service Unreachable**
   - Verify service selectors
   - Check port configurations

### Useful Commands

```bash
# Watch all pods
kubectl get pods -n datawarehouse -w

# Check resource usage
kubectl top pods -n datawarehouse

# Port forward for testing
kubectl port-forward service/frontend 8080:80 -n datawarehouse

# Check events
kubectl get events -n datawarehouse --sort-by='.lastTimestamp'
```

## Development vs Production

### Development
- Single replica deployments
- Basic resource limits
- Debug logging enabled

### Production Considerations
- Increase replica counts for high availability
- Set appropriate resource limits and requests
- Enable horizontal pod autoscaling
- Configure proper SSL/TLS
- Implement network policies
- Set up monitoring and alerting

## Migration from Docker Compose

This Kubernetes deployment maintains the same service architecture as the original Docker Compose setup:

- All environment variables preserved
- Same service dependencies
- Identical port mappings
- Same volume mounts

Key differences:
- Uses Kubernetes Secrets instead of environment variables for sensitive data
- Implements proper health checks and readiness probes
- Uses init containers for dependency management
- Configurable via Kustomize for different environments

## Support

For issues specific to this Kubernetes deployment:

1. Check the logs: `kubectl logs <pod-name> -n datawarehouse`
2. Verify configuration: `kubectl describe <resource> -n datawarehouse`
3. Review the Railway deployment guide: `railway-deployment-guide.md`
4. Check service dependencies and health checks

## Contributing

When modifying the Kubernetes manifests:

1. Update the appropriate base files
2. Test with `kustomize build railway`
3. Update documentation if needed
4. Verify all health checks work
5. Test the complete deployment flow
