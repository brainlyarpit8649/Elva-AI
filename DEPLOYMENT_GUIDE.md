# 🚀 MCP + SuperAGI Integration Deployment Guide
# Free-Tier Cloud Services Setup for Elva AI

## 📋 Overview
This guide will help you deploy the MCP + SuperAGI integration using only free-tier cloud services:
- **Railway** (Free Plan) - For MCP and SuperAGI deployment
- **Upstash** (Free) - Redis for fast context storage  
- **MongoDB Atlas** (Free) - Long-term context and conversation history
- **Groq** (Free API) - LLM processing for agents
- **n8n Cloud** (Free Plan) - Workflow automation

## 🔧 Step 1: Database Setup

### Upstash Redis (Free Tier)
1. Go to [upstash.com](https://upstash.com/)
2. Sign up for free account
3. Create new Redis database
4. Copy connection details:
   ```
   REDIS_URL="redis://default:your-password@redis-12345.upstash.io:6379"
   ```

### MongoDB Atlas (Free Tier)
1. Go to [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create free M0 cluster (512MB storage)
3. Create database user
4. Add IP whitelist: `0.0.0.0/0` (or your specific IPs)
5. Get connection string:
   ```
   MONGO_ATLAS_URL="mongodb+srv://username:password@cluster0.abc123.mongodb.net/elva_mcp_db"
   ```

## 🧠 Step 2: LLM API Setup

### Groq (Free API)
1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up for free account (14,400 requests/day)
3. Generate API key:
   ```
   GROQ_API_KEY="gsk_your_groq_api_key_here"
   ```

### Google Search API (Optional - for Research Agent)
1. Go to [console.developers.google.com](https://console.developers.google.com/)
2. Create project and enable Custom Search API
3. Create Custom Search Engine at [cse.google.com](https://cse.google.com/)
4. Get API key and Search Engine ID:
   ```
   GOOGLE_API_KEY="your_google_api_key"
   GOOGLE_CSE_ID="your_custom_search_engine_id"
   ```

## 🚄 Step 3: Railway Deployment

### Deploy MCP Service
1. Go to [railway.app](https://railway.app/)
2. Sign up and connect GitHub repository
3. Create new project from GitHub repo
4. Deploy MCP service:
   ```bash
   # In Railway dashboard:
   # - Set build command: docker build -f Dockerfile.mcp -t mcp-service .
   # - Set start command: python -m uvicorn mcp_service:app --host 0.0.0.0 --port $PORT
   ```

5. Set environment variables in Railway:
   ```
   MONGO_URL=<your-mongodb-atlas-url>
   REDIS_URL=<your-upstash-redis-url>
   MCP_API_TOKEN=mcp-secret-token-elva-ai-2024
   PORT=8002
   ```

6. Copy your Railway MCP service URL:
   ```
   MCP_SERVICE_URL="https://your-mcp-service.railway.app"
   ```

### Deploy SuperAGI
1. Create second Railway service for SuperAGI
2. Use SuperAGI Docker image:
   ```yaml
   # In Railway, use custom Docker configuration:
   FROM superagi/superagi:latest
   COPY agent-configs/ /app/configs/
   ```

3. Set environment variables:
   ```
   GROQ_API_KEY=<your-groq-key>
   MCP_SERVICE_URL=<your-mcp-railway-url>
   MCP_API_TOKEN=mcp-secret-token-elva-ai-2024
   SUPERAGI_API_KEY=superagi-elva-integration-2024
   DATABASE_URL=<railway-postgres-url>
   ```

4. Copy your Railway SuperAGI service URL:
   ```
   SUPERAGI_BASE_URL="https://your-superagi-service.railway.app"
   ```

## 🔧 Step 4: Update Elva AI Backend

### Update Environment Variables
Add to `/app/backend/.env`:
```bash
# MCP Integration
MCP_SERVICE_URL="https://your-mcp-service.railway.app"
MCP_API_TOKEN="mcp-secret-token-elva-ai-2024"

# SuperAGI Integration  
SUPERAGI_BASE_URL="https://your-superagi-service.railway.app"
SUPERAGI_API_KEY="superagi-elva-integration-2024"

# Free Tier Databases
REDIS_URL="redis://default:password@redis-12345.upstash.io:6379"
MONGO_ATLAS_URL="mongodb+srv://user:pass@cluster0.mongodb.net/elva_mcp_db"

# Optional: Google Search for Research Agent
GOOGLE_API_KEY="your_google_api_key"
GOOGLE_CSE_ID="your_cse_id"
```

### Restart Elva Backend
```bash
cd /app/backend
sudo supervisorctl restart backend
```

## 🌐 Step 5: Update n8n Workflows

### Modify Existing Workflows
1. Go to your n8n cloud dashboard
2. Update workflows to read from MCP before execution:

```javascript
// Add MCP Context Reader node before actions
const mcpResponse = await this.helpers.httpRequest({
  method: 'GET',
  url: 'https://your-mcp-service.railway.app/context/read/' + sessionId,
  headers: {
    'Authorization': 'Bearer mcp-secret-token-elva-ai-2024'
  }
});

const context = mcpResponse.context;
const appends = mcpResponse.appends;

// Use context data for email/LinkedIn posting
```

### Create New MCP-Integrated Workflows
1. **Email Workflow**: Read email summary from MCP → Send emails
2. **LinkedIn Workflow**: Read post package from MCP → Post to LinkedIn  
3. **Research Workflow**: Read research results from MCP → Share insights

## 🧪 Step 6: Testing the Integration

### Test MCP Service
```bash
# Health check
curl https://your-mcp-service.railway.app/health

# Test context write
curl -X POST https://your-mcp-service.railway.app/context/write \
  -H "Authorization: Bearer mcp-secret-token-elva-ai-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "user_id": "test-user", 
    "intent": "test_intent",
    "data": {"test": "data"}
  }'

# Test context read
curl https://your-mcp-service.railway.app/context/read/test-123 \
  -H "Authorization: Bearer mcp-secret-token-elva-ai-2024"
```

### Test SuperAGI Integration
```bash
# Test Elva → SuperAGI connection
curl -X POST https://b048af7a-e4e0-40c9-adb7-9aecb5206fca.preview.emergentagent.com/api/superagi/run-task \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "goal": "summarize my emails and create LinkedIn post idea",
    "agent_type": "auto"
  }'
```

### Test End-to-End Flow
1. Send message to Elva: "Summarize my last 5 emails and create a LinkedIn post idea"
2. Check MCP context was written: `/mcp/read-context/{session_id}`
3. Verify SuperAGI task execution: `/superagi/run-task`
4. Confirm results appear in Elva chat
5. Test "send" confirmation → n8n webhook execution

## 📊 Step 7: Monitoring and Maintenance

### Set Up Basic Monitoring
1. **Railway Metrics**: Monitor service health and usage
2. **Upstash Dashboard**: Track Redis usage and performance
3. **MongoDB Atlas**: Monitor database connections and storage
4. **Groq Console**: Track API usage and rate limits

### Resource Limits (Free Tier)
- **Railway**: $5 credit/month, 500 hours runtime
- **Upstash**: 10K commands/day, 256MB storage
- **MongoDB Atlas**: 512MB storage, 100 connections
- **Groq**: 14,400 requests/day
- **n8n Cloud**: 100 workflow executions/month

### Optimization Tips
1. **Cache frequently accessed data** in Redis
2. **Use Groq efficiently** - batch requests when possible
3. **Clean up old MCP contexts** regularly (24h TTL)
4. **Monitor Railway usage** to avoid overages
5. **Implement request rate limiting** to stay within API limits

## 🚨 Troubleshooting

### Common Issues
1. **MCP Service Not Responding**
   - Check Railway logs: `railway logs`
   - Verify environment variables
   - Test database connections

2. **SuperAGI Agent Errors**
   - Check Groq API key and usage limits
   - Verify MCP service accessibility
   - Review agent configuration

3. **Database Connection Issues**
   - Test MongoDB Atlas connection string
   - Verify Upstash Redis credentials
   - Check IP whitelist settings

4. **n8n Webhook Failures**
   - Verify MCP context reading logic
   - Check webhook authentication
   - Test context data structure

### Support Resources
- **Railway**: [docs.railway.app](https://docs.railway.app/)
- **Upstash**: [docs.upstash.com](https://docs.upstash.com/)
- **MongoDB Atlas**: [docs.atlas.mongodb.com](https://docs.atlas.mongodb.com/)
- **Groq**: [console.groq.com/docs](https://console.groq.com/docs)
- **SuperAGI**: [docs.superagi.com](https://docs.superagi.com/)

## ✅ Success Criteria

Your MCP + SuperAGI integration is successfully deployed when:

1. ✅ MCP service is accessible and responding to health checks
2. ✅ SuperAGI agents can read/write context via MCP
3. ✅ Elva writes context to MCP on every intent detection
4. ✅ SuperAGI tasks execute and return results to MCP
5. ✅ n8n workflows read final context before execution
6. ✅ End-to-end flow works: Elva → MCP → SuperAGI → MCP → Elva → n8n
7. ✅ All services run within free tier limits
8. ✅ Tablet-accessible dashboards for monitoring

## 🎯 Next Steps

After successful deployment:
1. **Scale gradually** - Monitor usage and upgrade tiers as needed
2. **Add more agents** - Create specialized agents for different tasks
3. **Enhance context sharing** - Add more data sources (calendar, docs, etc.)
4. **Implement advanced features** - Multi-agent collaboration, learning, etc.
5. **Monitor and optimize** - Track performance and optimize for cost efficiency

---

**Total Setup Time**: ~2-3 hours
**Monthly Cost**: $0 (all free tiers)
**Maintenance**: ~30 minutes/week for monitoring and optimization