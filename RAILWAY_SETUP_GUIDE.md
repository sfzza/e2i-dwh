# Railway Setup Guide - Step by Step

This guide will walk you through setting up your E2I Data Warehouse on Railway step by step.

## 🚀 **Step 1: Connect Your Repository**

1. Go to [Railway.app](https://railway.app)
2. Sign in with your GitHub account
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your repository: `sfzza/e2i-dwh`
6. Click **"Deploy Now"**

## 🗄️ **Step 2: Add PostgreSQL Database (CRITICAL)**

This is the most important step! Without this, your app will fail with database connection errors.

### Add PostgreSQL Addon:

1. In your Railway project dashboard
2. Click **"Add Service"**
3. Select **"Database"**
4. Choose **"PostgreSQL"**
5. Railway will automatically create the database

### Verify Database Connection:

1. Go to your **PostgreSQL service** in Railway
2. Click on the **"Variables"** tab
3. You should see `DATABASE_URL` automatically set
4. Copy this value for reference (it looks like: `postgresql://user:password@host:port/database`)

## ⚙️ **Step 3: Set Environment Variables**

Go to your main application service and set these environment variables:

### Required Variables:

```bash
DJANGO_SECRET_KEY=your-secret-key-here-change-this-in-production
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-app.railway.app
```

### How to Set Variables:

1. Click on your **main application service** (not the database)
2. Go to **"Variables"** tab
3. Click **"New Variable"**
4. Add each variable one by one

### Generate Secret Key:

```bash
# Generate a secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 🔧 **Step 4: Verify Configuration**

After adding the PostgreSQL addon, your Railway project should have:

1. **Main Application Service** - Your Django app
2. **PostgreSQL Service** - Your database
3. **Environment Variables** set correctly

### Check Variables:

Your main app should have these variables automatically:
- `DATABASE_URL` (provided by PostgreSQL addon)
- Plus the ones you manually added

## 🚀 **Step 5: Deploy and Monitor**

1. Railway will automatically redeploy when you add the database
2. Go to **"Deployments"** tab to monitor the build
3. Check the **"Logs"** for any errors

### Expected Success Logs:

```
🚀 Starting E2I Data Warehouse on Railway...
📁 Creating necessary directories...
📦 Installing Python dependencies...
✅ Using Railway DATABASE_URL for database connection
🗄️ Running database migrations...
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, ingestion, common
Running migrations:
  Applying migrations...
🔧 Collecting static files...
🌐 Starting Django development server...
✅ E2I Data Warehouse started successfully!
```

## 🔍 **Troubleshooting**

### If you see database connection errors:

1. **Check if PostgreSQL addon is added**:
   - Go to your Railway project
   - You should see TWO services: your app + PostgreSQL
   - If you only see one service, add PostgreSQL addon

2. **Check DATABASE_URL variable**:
   - Go to your main app service
   - Check "Variables" tab
   - `DATABASE_URL` should be present and not empty

3. **Verify environment variables**:
   - Make sure `DJANGO_SECRET_KEY` is set
   - Make sure `DJANGO_DEBUG=False`
   - Make sure `DJANGO_ALLOWED_HOSTS` includes your Railway domain

### Common Issues:

**Error: "could not translate host name 'orchestrator_postgres'"**
- **Solution**: Add PostgreSQL addon to Railway (Step 2)

**Error: "No database configuration found!"**
- **Solution**: Verify PostgreSQL addon is added and DATABASE_URL is set

**Error: "SECRET_KEY not set"**
- **Solution**: Set DJANGO_SECRET_KEY environment variable

## 📊 **Step 6: Access Your Application**

Once deployed successfully:

1. Railway will provide a public URL (e.g., `https://your-app.railway.app`)
2. Visit the URL to access your E2I Data Warehouse
3. The Django admin will be available at `/admin/`

## 🎯 **Quick Checklist**

- [ ] Repository connected to Railway
- [ ] PostgreSQL addon added
- [ ] DATABASE_URL environment variable present
- [ ] DJANGO_SECRET_KEY set
- [ ] DJANGO_DEBUG=False
- [ ] DJANGO_ALLOWED_HOSTS configured
- [ ] Application deployed successfully
- [ ] No database connection errors in logs

## 🆘 **Need Help?**

If you're still having issues:

1. Check the **Railway logs** for specific error messages
2. Verify all **environment variables** are set correctly
3. Ensure **PostgreSQL addon** is added
4. Check the **troubleshooting guide**: `RAILWAY_TROUBLESHOOTING.md`

## 🎉 **Success!**

Once everything is working, you'll have:
- ✅ Django application running on Railway
- ✅ PostgreSQL database connected
- ✅ All dependencies installed
- ✅ Database migrations applied
- ✅ Static files collected
- ✅ Application accessible via public URL

Your E2I Data Warehouse is now live on Railway! 🚀
