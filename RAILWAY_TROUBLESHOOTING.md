# Railway Deployment Troubleshooting Guide

## 🚨 Common Issues and Solutions

### Issue: Django Logging Configuration Error

**Error Message:**
```
ValueError: Unable to configure handler 'file'
FileNotFoundError: [Errno 2] No such file or directory: '/app/logs/django.log'
```

**Solution:**
✅ **Fixed** - The startup script now creates the necessary directories:
- Updated `start.sh` to create `/app/logs` directory
- Updated `Dockerfile` to create directories during build
- Updated Django settings to ensure directory exists
- Changed logging to console-only for Railway (better for cloud deployment)

### Issue: Database Connection Errors

**Error Message:**
```
django.db.utils.OperationalError: could not connect to server
```

**Solution:**
1. **Add PostgreSQL Addon** in Railway dashboard
2. **Set Environment Variables** (Railway provides these automatically):
   ```bash
   DATABASE_URL=postgresql://user:password@host:port/database
   ```
3. **Or set manually:**
   ```bash
   DJANGO_DB_HOST=your-db-host.railway.app
   DJANGO_DB_USER=postgres
   DJANGO_DB_PASSWORD=your-password
   DJANGO_DB_NAME=railway
   ```

### Issue: Port Configuration

**Error Message:**
```
Error: Port already in use
```

**Solution:**
✅ **Fixed** - The application now uses Railway's `$PORT` environment variable:
```bash
python manage.py runserver 0.0.0.0:$PORT
```

### Issue: Static Files Collection

**Error Message:**
```
Permission denied: '/app/static'
```

**Solution:**
✅ **Fixed** - Updated permissions in Dockerfile:
```dockerfile
RUN chmod -R 755 /app
```

### Issue: Missing Dependencies

**Error Message:**
```
ModuleNotFoundError: No module named 'pandas'
ModuleNotFoundError: No module named 'django'
```

**Solution:**
✅ **Fixed** - Updated requirements.txt with all necessary dependencies:
```bash
# Added data processing libraries
pandas>=1.5.0
numpy>=1.21.0
openpyxl>=3.0.0
xlrd>=2.0.0
xlsxwriter>=3.0.0
```

✅ **Fixed** - Dependencies are installed in startup script:
```bash
pip install -r requirements.txt
```

## 🔧 Environment Variables Setup

### Required Environment Variables

Set these in your Railway dashboard:

```bash
# Django
DJANGO_SETTINGS_MODULE=e2i_api.settings
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ALLOWED_HOSTS=your-app.railway.app

# Database (automatically provided by Railway PostgreSQL addon)
DATABASE_URL=postgresql://...
```

### Optional Environment Variables

```bash
# External Services (if not using Railway addons)
MINIO_ENDPOINT=your-minio-endpoint
CLICKHOUSE_HOST=your-clickhouse-host
REDIS_URL=your-redis-url
```

## 🚀 Deployment Steps

### 1. Connect Repository
- Go to Railway dashboard
- Connect your GitHub repository: `sfzza/e2i-dwh`

### 2. Add PostgreSQL Database
- Add PostgreSQL addon in Railway
- Railway will automatically set `DATABASE_URL`

### 3. Set Environment Variables
- Go to Variables tab in Railway
- Add required environment variables
- Copy from `railway-env-example.txt`

### 4. Deploy
- Railway will automatically build and deploy
- Monitor logs in Railway dashboard

## 📊 Monitoring and Debugging

### View Logs
```bash
# In Railway dashboard
# Go to Deployments > View Logs

# Or use Railway CLI
railway logs
```

### Check Application Status
```bash
# Health check endpoint
curl https://your-app.railway.app/health
```

### Common Log Patterns

**Successful Startup:**
```
🚀 Starting E2I Data Warehouse on Railway...
📁 Creating necessary directories...
📦 Installing Python dependencies...
🗄️ Running database migrations...
🔧 Collecting static files...
🌐 Starting Django development server...
✅ E2I Data Warehouse started successfully!
```

**Database Connection Success:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, ingestion, common
Running migrations:
  Applying migrations...
```

## 🛠️ Development vs Production

### Development (Local)
```bash
# Use Docker Compose
docker-compose up -d

# Or run directly
cd e2i/backend
python manage.py runserver
```

### Production (Railway)
- Automatic builds from GitHub
- Environment variables in Railway dashboard
- Managed PostgreSQL database
- Auto-scaling and monitoring

## 🔒 Security Best Practices

### Environment Variables
- ✅ Never commit secrets to Git
- ✅ Use Railway's environment variables
- ✅ Rotate secrets regularly
- ✅ Use strong, unique passwords

### Database Security
- ✅ Use Railway's managed PostgreSQL
- ✅ Enable SSL connections
- ✅ Regular backups
- ✅ Access control

## 📈 Performance Optimization

### Railway Auto-Scaling
- Automatic scaling based on traffic
- Resource limits configurable
- Cost optimization with usage-based pricing

### Application Optimization
- Enable caching with Redis
- Use CDN for static files
- Database connection pooling
- Optimize Django settings

## 🆘 Getting Help

### Railway Support
- [Railway Documentation](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- [Railway GitHub](https://github.com/railwayapp)

### Application Issues
- Check logs in Railway dashboard
- Verify environment variables
- Test database connectivity
- Review Django settings

### Common Commands
```bash
# Check deployment status
railway status

# View logs
railway logs

# Connect to container (if needed)
railway shell

# Check environment variables
railway variables
```

## ✅ Success Checklist

- [ ] Repository connected to Railway
- [ ] PostgreSQL addon added
- [ ] Environment variables set
- [ ] Application builds successfully
- [ ] Database migrations run
- [ ] Application starts without errors
- [ ] Health check endpoint responds
- [ ] Logs show successful startup

Your E2I Data Warehouse should now be running successfully on Railway! 🎉
