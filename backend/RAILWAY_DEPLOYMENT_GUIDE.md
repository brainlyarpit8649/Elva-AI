# MCP Service Deployment Guide - Railway

## 🚀 Deployment Instructions

### Step 1: Create Railway Project
1. Go to https://railway.app/
2. Sign in with GitHub
3. Click "New Project" 
4. Select "Deploy from GitHub repo"
5. Connect to your repository containing the MCP service

### Step 2: Configure Build Settings
Use the following configuration:

**Build Command:**
```bash
# No build command needed (using Dockerfile)
```

**Dockerfile Path:**
```
Dockerfile.mcp
```

**Port Configuration:**
```
PORT=8002
```

### Step 3: Environment Variables
Set these environment variables in Railway dashboard:

```env
MCP_API_TOKEN=kumararpit9468
MCP_REDIS_URL=rediss://default:ARTGAAIjcDFjNWNlOTRjZDY5ODM0YTBjOTI2MTc3NzhmNzg3YzBkNnAxMA@brave-deer-5318.upstash.io:6379
MCP_MONGO_URI=mongodb+srv://kumararpit9468:kumararpit1234coc@elva-mcp-mongo.uzclf39.mongodb.net/elva_mcp?retryWrites=true&w=majority&appName=elva-mcp-mongo
MCP_DB_NAME=elva_mcp
PORT=8002
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Step 4: Deploy
1. Commit and push your changes to GitHub
2. Railway will automatically detect the Dockerfile.mcp
3. The service will build and deploy
4. You'll get a URL like: `https://mcp-service-production.up.railway.app`

### Step 5: Verify Deployment
Test the deployed service:

```bash
# Health check
curl https://your-railway-url.railway.app/health

# Test write endpoint
curl -X POST "https://your-railway-url.railway.app/context/write" \
  -H "Authorization: Bearer kumararpit9468" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "intent": "test", "data": {}}'
```

## 📋 Expected Railway URL Format
Your MCP service will be available at:
```
https://mcp-service-production-xxxx.up.railway.app
```

## 🔧 Troubleshooting
- Check Railway logs for deployment issues
- Verify all environment variables are set correctly
- Ensure Redis and MongoDB connections are working
- Check the health endpoint first

## 🎯 Success Indicators
- Health endpoint returns 200 OK
- MongoDB and Redis connections show "connected"
- All endpoints respond with proper authentication
- Write → Read → Append flow works correctly