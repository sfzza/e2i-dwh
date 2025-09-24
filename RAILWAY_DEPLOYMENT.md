# Railway Deployment Guide for E2I Data Warehouse

This guide explains how to deploy your E2I Data Warehouse application to Railway using the provided configuration files.

## 🚀 Quick Start

### Option 1: Single Service Deployment (Recommended for Railway)

Railway works best with single-service deployments. The current configuration deploys the Django backend as the primary service.

**Files Created:**
- `start.sh` - Startup script for Railway
- `railway.json` - Railway configuration
- `Dockerfile` - Main Docker build file

### Deploy to Railway

1. **Connect your GitHub repository** to Railway
2. **Railway will automatically detect** the configuration files
3. **Deploy** - Railway will build and deploy your Django backend

### Environment Variables

Set these environment variables in Railway dashboard:

```bash
# Database (use Railway PostgreSQL addon)
DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=<railway-postgres-db>
DJANGO_DB_USER=<railway-postgres-user>
DJANGO_DB_PASSWORD=<railway-postgres-password>
DJANGO_DB_HOST=<railway-postgres-host>
DJANGO_DB_PORT=5432

# Django Settings
DJANGO_SETTINGS_MODULE=e2i_api.settings
DJANGO_DEBUG=False
SECRET_KEY=<your-secret-key>

# Optional: Other services (if using external services)
MINIO_ENDPOINT=<your-minio-endpoint>
CLICKHOUSE_HOST=<your-clickhouse-host>
REDIS_URL=<your-redis-url>
```

## 🏗️ Architecture Options

### Option 1: Single Service (Current Setup)
- **Primary Service**: Django Backend
- **Database**: Railway PostgreSQL addon
- **Storage**: Railway volume or external storage
- **Other Services**: Use external managed services

### Option 2: Multi-Service (Advanced)
For a complete multi-service deployment, you'll need to:

1. **Create separate Railway projects** for each service
2. **Use Railway's service discovery** for inter-service communication
3. **Deploy each service individually**

## 📁 Service Breakdown

### Primary Service (Django Backend)
- **File**: `Dockerfile`, `start.sh`
- **Purpose**: Main API and data processing
- **Port**: Railway will assign automatically
- **Database**: Railway PostgreSQL

### Additional Services (Optional External)
- **Airflow**: Use external Airflow service or Railway addon
- **ClickHouse**: Use external ClickHouse service
- **Redis**: Use Railway Redis addon
- **MinIO**: Use external object storage
- **Frontend**: Deploy separately as static site

## 🔧 Configuration Details

### start.sh
```bash
#!/bin/bash
# Starts Django with proper Railway configuration
# Runs migrations, collects static files, starts server
```

### railway.json
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "bash start.sh",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### Dockerfile
- **Base**: Python 3.11 slim
- **Dependencies**: PostgreSQL client, build tools
- **Health Check**: Built-in health endpoint
- **Port**: Uses Railway's PORT environment variable

## 🗄️ Database Setup

### Railway PostgreSQL Addon

1. **Add PostgreSQL addon** in Railway dashboard
2. **Copy connection details** to environment variables
3. **Django will automatically connect** on startup

### Migration Strategy

The startup script automatically runs:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## 🌐 Accessing Your Application

After deployment:

1. **Railway will provide** a public URL
2. **Access your Django API** at: `https://your-app.railway.app`
3. **Health check** available at: `https://your-app.railway.app/health`

## 🔍 Monitoring and Logs

### Railway Dashboard
- **Build logs**: View in Railway dashboard
- **Runtime logs**: Real-time application logs
- **Metrics**: CPU, memory, network usage

### Application Logs
```bash
# View logs in Railway dashboard or CLI
railway logs
```

## 🛠️ Development Workflow

### Local Development
```bash
# Use Docker Compose for local development
docker-compose up -d

# Or run Django directly
cd e2i/backend
python manage.py runserver
```

### Production Deployment
1. **Push to GitHub**
2. **Railway auto-deploys**
3. **Monitor in Railway dashboard**

## 🔒 Security Considerations

### Environment Variables
- **Never commit secrets** to Git
- **Use Railway's environment variables** for sensitive data
- **Rotate secrets regularly**

### Database Security
- **Use Railway's managed PostgreSQL**
- **Enable SSL connections**
- **Regular backups**

## 📊 Scaling

### Railway Auto-Scaling
- **Automatic scaling** based on traffic
- **Resource limits** configurable in Railway
- **Cost optimization** with usage-based pricing

### Performance Optimization
- **Enable caching** with Redis
- **Use CDN** for static files
- **Database connection pooling**

## 🆘 Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check build logs in Railway dashboard
   # Verify Dockerfile syntax
   # Check dependencies in requirements.txt
   ```

2. **Database Connection Issues**
   ```bash
   # Verify environment variables
   # Check PostgreSQL addon status
   # Test connection from Railway dashboard
   ```

3. **Application Startup Issues**
   ```bash
   # Check start.sh script
   # Verify Python dependencies
   # Check Django settings
   ```

### Debug Commands

```bash
# Check application status
railway status

# View logs
railway logs

# Connect to running container
railway shell
```

## 🔄 Migration from Docker Compose

### Key Differences

| Docker Compose | Railway |
|----------------|---------|
| Multiple services | Single service (Django) |
| Local networking | External service discovery |
| Volume mounts | Railway volumes |
| Environment files | Railway environment variables |
| Manual scaling | Auto-scaling |

### Migration Steps

1. **Choose primary service** (Django backend)
2. **Create Railway configuration**
3. **Set up external services** (PostgreSQL, Redis, etc.)
4. **Update connection strings**
5. **Deploy and test**

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Django on Railway](https://docs.railway.app/guides/django)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)
- [Environment Variables](https://docs.railway.app/variables-and-secrets)

## 🎯 Next Steps

1. **Deploy to Railway** using the provided configuration
2. **Set up external services** as needed
3. **Configure domain** and SSL
4. **Set up monitoring** and alerts
5. **Optimize performance** based on usage

Your E2I Data Warehouse is now ready for Railway deployment! 🚀
