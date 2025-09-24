# Railway Deployment Crash Troubleshooting

## 🚨 **Your Deployment Crashed - Let's Fix It!**

Even though the PostgreSQL database started successfully, your Django application crashed. Here's how to diagnose and fix the issue.

## 🔍 **Step 1: Check Railway Logs**

1. Go to your Railway project dashboard
2. Click on your **main application service** (not the database)
3. Go to **"Deployments"** tab
4. Click on the **latest deployment**
5. Check the **"Logs"** section

Look for error messages that indicate what went wrong.

## 🚨 **Common Crash Causes & Solutions**

### **1. Database Connection Still Failing**

**Symptoms:**
```
django.db.utils.OperationalError: could not translate host name "orchestrator_postgres"
```

**Solution:**
The Django app might have started before the database was fully ready. Railway should automatically redeploy.

### **2. Missing Environment Variables**

**Symptoms:**
```
SECRET_KEY not set
DJANGO_ALLOWED_HOSTS not configured
```

**Solution:**
Add these environment variables in Railway dashboard:
```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-app.railway.app
```

### **3. Import Errors**

**Symptoms:**
```
ModuleNotFoundError: No module named 'pandas'
ImportError: cannot import name 'some_module'
```

**Solution:**
The requirements.txt should have all dependencies. Check if the build completed successfully.

### **4. Port Configuration Issues**

**Symptoms:**
```
Error: Port already in use
Address already in use
```

**Solution:**
The app should use Railway's `$PORT` environment variable automatically.

### **5. Static Files Issues**

**Symptoms:**
```
Permission denied: '/app/static'
Directory does not exist: '/app/static'
```

**Solution:**
The directories should be created automatically by our updated scripts.

## 🔧 **Step 2: Manual Diagnosis**

If you can access Railway CLI, run:

```bash
# Check deployment status
railway status

# View recent logs
railway logs --tail 100

# Check environment variables
railway variables
```

## 🚀 **Step 3: Force Redeploy**

Sometimes a simple redeploy fixes the issue:

1. Go to your Railway project
2. Click on your main application service
3. Go to **"Deployments"** tab
4. Click **"Redeploy"** or **"Deploy Latest"**

## 🔍 **Step 4: Check Environment Variables**

Make sure these are set in your main application service:

### Required Variables:
```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-app.railway.app
```

### How to Set:
1. Click on your **main application service**
2. Go to **"Variables"** tab
3. Add each variable

### Generate Secret Key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 🚨 **Step 5: Common Fixes**

### Fix 1: Add Missing Environment Variables
```bash
# In Railway dashboard, add these variables to your main app:
DJANGO_SECRET_KEY=django-insecure-your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*.railway.app
```

### Fix 2: Check Database Connection
The database should be connected automatically via `DATABASE_URL`. If not:
1. Verify PostgreSQL addon is added
2. Check that `DATABASE_URL` is visible in your app's environment variables

### Fix 3: Verify Build Success
Make sure the build completed without errors:
1. Check **"Build Logs"** in Railway
2. Look for successful installation of all packages
3. Verify no import errors during build

## 📋 **Step 6: Debug Checklist**

- [ ] PostgreSQL addon is added and running
- [ ] DATABASE_URL environment variable is present
- [ ] DJANGO_SECRET_KEY is set
- [ ] DJANGO_DEBUG=False
- [ ] DJANGO_ALLOWED_HOSTS is configured
- [ ] Build completed successfully
- [ ] No import errors in logs
- [ ] Database connection successful

## 🆘 **Step 7: Get Help**

If you're still having issues:

1. **Share the error logs** from Railway
2. **Check environment variables** are set correctly
3. **Verify PostgreSQL addon** is connected
4. **Try redeploying** the application

## 🔄 **Step 8: Quick Recovery**

If nothing else works, try this:

1. **Delete and recreate** the main application service
2. **Keep the PostgreSQL database** (don't delete it)
3. **Set environment variables** again
4. **Redeploy** from GitHub

## 📊 **Expected Success Logs**

When working correctly, you should see:
```
🚀 Starting E2I Data Warehouse on Railway...
📁 Creating necessary directories...
📦 Installing Python dependencies...
🔍 Checking database configuration...
✅ DATABASE_URL is set
✅ Using Railway DATABASE_URL for database connection
✅ Database connection successful!
🗄️ Running database migrations...
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, ingestion, common
Running migrations:
  Applying migrations...
🔧 Collecting static files...
🌐 Starting Django development server...
✅ E2I Data Warehouse started successfully!
```

## 🎯 **Most Likely Issue**

Based on the PostgreSQL logs you showed, the most likely issue is that the Django application started before the database was fully ready, or environment variables are missing.

**Quick Fix:**
1. Add the required environment variables
2. Force a redeploy
3. Monitor the logs for success

Let me know what error messages you see in the Railway logs, and I can help you fix the specific issue! 🚀
