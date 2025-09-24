# Frontend Deployment Fix Guide

## 🚨 **Issue**: Railway showing default API page instead of React app

## 🔧 **Solution Steps**

### **Step 1: Update Railway Project Settings**

1. Go to your **frontend Railway project**
2. Go to **"Settings"** → **"Build"**
3. Make sure **"Root Directory"** is set to: `e2i/frontend`
4. **Builder** should be: `Dockerfile`
5. **Dockerfile Path** should be: `e2i/frontend/Dockerfile`

### **Step 2: Set Environment Variables**

In your frontend Railway project, add these environment variables:

```bash
NODE_ENV=production
REACT_APP_API_URL=https://e2i-dwh-production.up.railway.app
PORT=3000
```

### **Step 3: Force Redeploy**

1. Go to **"Deployments"** tab
2. Click **"Redeploy"** or **"Deploy Latest"**
3. Wait for the build to complete

### **Step 4: Check Build Logs**

Monitor the build process for:
- ✅ Node.js installation
- ✅ Package installation (`pnpm install`)
- ✅ React build (`pnpm build`)
- ✅ Serve installation
- ✅ Application startup

## 🎯 **Expected Build Logs**

You should see logs like:
```
Step 1/12 : FROM node:18-alpine
Step 2/12 : WORKDIR /app
Step 3/12 : COPY package*.json ./
Step 4/12 : RUN npm install -g pnpm
Step 5/12 : RUN pnpm install
Step 6/12 : COPY . .
Step 7/12 : RUN pnpm build
Step 8/12 : RUN npm install -g serve
...
Starting serve on port 3000
```

## 🚨 **Common Issues & Fixes**

### **Issue 1: Wrong Root Directory**
- **Symptom**: Build fails or shows default Railway page
- **Fix**: Set Root Directory to `e2i/frontend`

### **Issue 2: Build Fails**
- **Symptom**: Build process fails
- **Fix**: Check package.json and dependencies

### **Issue 3: Port Issues**
- **Symptom**: App starts but not accessible
- **Fix**: Ensure PORT environment variable is set

### **Issue 4: Missing Environment Variables**
- **Symptom**: App loads but API calls fail
- **Fix**: Set `REACT_APP_API_URL` to your backend URL

## 🔍 **Verify Deployment**

After successful deployment, you should see:
- ✅ Your React application (not Railway default page)
- ✅ E2I Data Platform interface
- ✅ Connection to backend API working

## 📋 **Troubleshooting Checklist**

- [ ] Root Directory set to `e2i/frontend`
- [ ] Builder set to `Dockerfile`
- [ ] Environment variables configured
- [ ] Build completes successfully
- [ ] App serves on correct port
- [ ] API URL points to backend

## 🚀 **Alternative: Manual Deployment**

If Railway auto-detection isn't working:

1. **Delete the current deployment**
2. **Create new project**
3. **Select "Deploy from GitHub"**
4. **Choose your repo**: `sfzza/e2i-dwh`
5. **Set Root Directory**: `e2i/frontend`
6. **Set Builder**: `Dockerfile`
7. **Add environment variables**
8. **Deploy**

Your React frontend should now serve properly instead of the Railway default page! 🎉
