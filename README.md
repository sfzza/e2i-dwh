# E2I Data Warehouse - Kubernetes Deployment

A comprehensive data warehouse solution with ETL capabilities, migrated from Docker Compose to Kubernetes for Railway deployment.

## 🏗️ Architecture

This project includes a complete data warehouse stack with the following components:

### Core Services
- **PostgreSQL Databases** (4 instances): Airflow metadata, E2I application data, Tokenization data, Metabase data
- **Redis**: Caching and session storage
- **ClickHouse**: Analytics database for high-performance queries
- **MinIO**: Object storage for file uploads and data exports

### Application Services
- **Airflow**: Workflow orchestration (webserver + scheduler)
- **Django Backend**: Main API and data processing
- **Orchestrator**: Service coordination and workflow management
- **Reporting Service**: Data export and reporting capabilities
- **Tokenization Service**: Data privacy and tokenization
- **React Frontend**: User interface
- **Metabase**: Business intelligence and analytics dashboard

## 🚀 Quick Start

### Option 1: Railway Single Service Deployment (Recommended)

**Prerequisites:**
- Railway account
- GitHub repository connected to Railway

**Deploy to Railway:**
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the configuration files
3. Set environment variables in Railway dashboard
4. Deploy automatically

**Configuration Files Created:**
- `start.sh` - Startup script
- `railway.json` - Railway configuration
- `Dockerfile` - Main Docker build file

### Option 2: Kubernetes Multi-Service Deployment

**Prerequisites:**
- Railway account with Kubernetes support
- `kubectl` configured for Railway cluster
- `kustomize` installed
- Docker images built and pushed to accessible registry

**Deploy to Railway:**
```bash
cd e2i/infra/k8s
chmod +x railway-deploy.sh
./railway-deploy.sh deploy
```

### Access Services

After deployment, access services locally using port-forwarding:

```bash
# Frontend
kubectl port-forward service/frontend 8080:80 -n datawarehouse
# Visit: http://localhost:8080

# Django API
kubectl port-forward service/django 8081:8001 -n datawarehouse
# Visit: http://localhost:8081

# Airflow
kubectl port-forward service/airflow-webserver 8082:8080 -n datawarehouse
# Visit: http://localhost:8082 (admin: airflow/airflow)

# Metabase
kubectl port-forward service/metabase 8083:3000 -n datawarehouse
# Visit: http://localhost:8083
```

## 📁 Project Structure

```
├── e2i/
│   ├── backend/                 # Django application
│   ├── frontend/                # React frontend
│   ├── orchestrator/            # FastAPI orchestrator
│   └── infra/k8s/               # Kubernetes manifests
│       ├── base/                # Base Kubernetes configurations
│       ├── railway.yaml         # Railway-specific configuration
│       ├── railway-deploy.sh    # Deployment script
│       └── railway-deployment-guide.md
├── tokenization-service/         # Data tokenization service
├── etl-platform/                # ETL platform components
├── docker-compose.yml           # Original Docker Compose setup
├── Dockerfile                   # Main Railway Dockerfile
├── start.sh                     # Railway startup script
├── railway.json                 # Railway configuration
├── RAILWAY_DEPLOYMENT.md        # Railway deployment guide
└── README.md                    # This file
```

## 🔧 Configuration

### Before Deployment

1. **Update Image References**: Edit `e2i/infra/k8s/railway-patches.yaml` with your actual Docker image references
2. **Configure Secrets**: Update `e2i/infra/k8s/base/secrets.yaml` with your base64-encoded secrets
3. **Set Domain**: Replace `your-domain.com` in `e2i/infra/k8s/base/ingress.yaml` with your Railway domain

### Generate Base64 Secrets

```bash
# Example: Generate base64 for passwords
echo -n "your-password" | base64

# Update secrets.yaml with your actual values
```

## 🐳 Docker Images

Build and push your Docker images before deployment:

```bash
# Build images
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

## 🔍 Service Endpoints

| Service | Internal Port | External Access | Description |
|---------|---------------|-----------------|-------------|
| Frontend | 80 | `/` | React application |
| Django API | 8001 | `/api/v1` | Main API endpoints |
| Orchestrator | 8002 | `/orchestrator` | Service coordination |
| Reporting | 8003 | `/reporting` | Data export service |
| Tokenization | 8004 | `/tokenization` | Data privacy service |
| Airflow | 8080 | `/airflow` | Workflow orchestration |
| Metabase | 3000 | `/metabase` | Analytics dashboard |

## 🛠️ Development

### Local Development with Docker Compose

For local development, you can still use the original Docker Compose setup:

```bash
docker-compose up -d
```

### Kubernetes Development

```bash
# Check deployment status
./railway-deploy.sh status

# View logs
kubectl logs -f deployment/django -n datawarehouse

# Clean up
./railway-deploy.sh cleanup
```

## 📊 Monitoring

All services include health check endpoints:

- Django: `/health`
- Orchestrator: `/health`
- Tokenization: `/api/v1/health`
- Frontend: `/`
- Airflow: `/health`

## 🔒 Security

- Secrets managed via Kubernetes Secrets
- ConfigMaps for non-sensitive configuration
- Proper service isolation
- Health checks for all services

## 📚 Documentation

- **Kubernetes Deployment**: `e2i/infra/k8s/README.md`
- **Railway Deployment Guide**: `e2i/infra/k8s/railway-deployment-guide.md`
- **Original Docker Setup**: `docker-compose.yml`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the deployment
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the logs: `kubectl logs <pod-name> -n datawarehouse`
2. Review the deployment guide: `e2i/infra/k8s/railway-deployment-guide.md`
3. Verify configuration and secrets
4. Check service dependencies and health checks

## 🔄 Migration Notes

This Kubernetes deployment maintains the same service architecture as the original Docker Compose setup:

- All environment variables preserved
- Same service dependencies
- Identical port mappings
- Same volume mounts

Key improvements:
- Kubernetes Secrets for sensitive data
- Proper health checks and readiness probes
- Init containers for dependency management
- Configurable via Kustomize for different environments
- Railway-optimized configuration# e2i-dwh
