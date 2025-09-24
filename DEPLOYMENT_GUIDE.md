# 🌐 Datawarehouse Public Deployment Guide

This guide will help you deploy your datawarehouse application so anyone can access it from the internet.

## 🚀 Quick Start Options

### Option 1: Immediate Public Access (ngrok) - 2 minutes
**Perfect for demos, testing, or temporary access**

```bash
# 1. Start port forwarding for Metabase (working service)
kubectl port-forward -n datawarehouse svc/metabase 8080:3000 &

# 2. Start ngrok tunnel
ngrok http 8080

# 3. Share the ngrok URL (e.g., https://abc123.ngrok.io)
```

**✅ What's accessible:**
- Metabase BI Dashboard: `https://[random-id].ngrok.io`
- Real-time analytics and reporting
- Interactive dashboards

### Option 2: Google Cloud Platform (GCP) - 15 minutes
**Best for production with custom domain**

```bash
# 1. Run the GCP deployment script
cd e2i/infra/k8s
./deploy-to-gcp.sh

# 2. Follow the prompts to enter your domain
# 3. Configure DNS as instructed
# 4. Access via your custom domain
```

**✅ What you get:**
- Custom domain (e.g., `mydatawarehouse.com`)
- SSL certificates (automatic)
- Scalable infrastructure
- Professional setup

### Option 3: Other Cloud Providers
**AWS, DigitalOcean, Azure options available**

```bash
# Run the quick deployment script
cd e2i/infra/k8s
./quick-deploy.sh

# Choose your preferred cloud provider
```

## 📊 Current Service Status

### ✅ Working Services (Ready for Public Access)
- **Metabase** - BI Dashboard and Analytics
- **PostgreSQL Databases** - Data storage
- **ClickHouse** - Analytics database
- **Redis** - Caching layer

### 🔧 Services Being Fixed
- **Django Backend** - Main API (image pull issues)
- **Frontend** - React application (image pull issues)
- **Airflow** - Workflow orchestration (configuration issues)
- **MinIO** - Object storage (configuration issues)

## 🌐 Public Access URLs

### Current Working Access:
```bash
# Metabase Dashboard (via ngrok)
https://[ngrok-url].ngrok.io

# Local access (if running locally)
http://localhost:8080  # Metabase
http://localhost:8081  # Airflow (when fixed)
http://localhost:8082  # ClickHouse
```

### After Full Deployment:
```bash
# With custom domain
https://yourdomain.com           # Main application
https://airflow.yourdomain.com   # Airflow
https://metabase.yourdomain.com  # Metabase
```

## 🛠️ Troubleshooting

### Fix Image Pull Issues:
```bash
# Rebuild images in minikube environment
eval $(minikube docker-env)
docker build -f e2i/backend/Dockerfile.django -t django-backend:latest ./e2i/backend/
docker build -f e2i/frontend/Dockerfile -t frontend:latest ./e2i/frontend/

# Restart deployments
kubectl rollout restart deployment/django-backend -n datawarehouse
kubectl rollout restart deployment/frontend -n datawarehouse
```

### Check Service Status:
```bash
# View all services
kubectl get all -n datawarehouse

# Check pod logs
kubectl logs -n datawarehouse deployment/metabase
kubectl logs -n datawarehouse deployment/django-backend

# Check service endpoints
kubectl get svc -n datawarehouse
```

## 🔐 Security Considerations

### For Production Deployment:
1. **Change default passwords** in `secrets.yaml`
2. **Use proper SSL certificates**
3. **Configure authentication**
4. **Set up monitoring and logging**
5. **Use secrets management**

### Current Default Credentials:
- Airflow: `airflow` / `airflow`
- Metabase: `admin` / `admin`
- MinIO: `minioadmin` / `minioadmin`

## 📈 Scaling Options

### Horizontal Scaling:
```bash
# Scale Django backend
kubectl scale deployment django-backend --replicas=3 -n datawarehouse

# Scale Airflow workers
kubectl scale deployment airflow-scheduler --replicas=2 -n datawarehouse
```

### Resource Limits:
```bash
# Check resource usage
kubectl top pods -n datawarehouse
kubectl top nodes
```

## 🎯 Next Steps

1. **Immediate**: Use ngrok for quick public access
2. **Short-term**: Fix image issues and deploy to cloud
3. **Long-term**: Set up proper domain, SSL, and monitoring

## 📞 Support

If you encounter issues:
1. Check the logs: `kubectl logs -n datawarehouse [pod-name]`
2. Verify images: `docker images | grep [service-name]`
3. Check network: `kubectl get svc -n datawarehouse`

---

**🎉 Your datawarehouse is ready for public access!**
