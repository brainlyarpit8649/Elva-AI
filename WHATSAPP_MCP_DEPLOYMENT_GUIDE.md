# WhatsApp MCP Production Deployment Guide

## 🚀 Production MCP Service Setup

### **Deployment URL**
```
https://elva-mcp-service.onrender.com
```

### **WhatsApp MCP Endpoint**
```
POST https://elva-mcp-service.onrender.com/api/mcp
```

### **Bearer Token**
```
kumararpit9468
```
*(Set via MCP_API_TOKEN environment variable)*

---

## 📱 **Puch AI Integration Command**

### **Option 1: Token via Query Parameter**
```bash
/mcp connect https://elva-mcp-service.onrender.com/api/mcp?token=kumararpit9468
```

### **Option 2: Token via Authorization Header**
```bash
URL: https://elva-mcp-service.onrender.com/api/mcp
Authorization: Bearer kumararpit9468
```

---

## 🔧 **Environment Variables for Production**

Deploy the MCP service with these environment variables:

```env
# MCP Service Configuration
MCP_API_TOKEN=kumararpit9468
ELVA_BACKEND_URL=https://0b30aab1-896e-477e-822b-002edcbac2b3.preview.emergentagent.com

# MongoDB Atlas Configuration
MCP_MONGO_URI=mongodb+srv://kumararpit9468:kumararpit1234coc@elva-mcp-mongo.uzclf39.mongodb.net/elva_mcp?retryWrites=true&w=majority&appName=elva-mcp-mongo
MCP_DB_NAME=elva_mcp

# Redis Configuration
MCP_REDIS_URL=rediss://default:ARTGAAIjcDFjNWNlOTRjZDY5ODM0YTBjOTI2MTc3NzhmNzg3YzBkNnAxMA@brave-deer-5318.upstash.io:6379

# Production Settings
ENVIRONMENT=production
PORT=8002
HOST=0.0.0.0
```

---

## 📋 **Message Format for Puch AI**

When Puch AI sends WhatsApp messages to the MCP endpoint:

```json
{
  "session_id": "unique_whatsapp_session_id",
  "message": "user's WhatsApp message content",
  "user_id": "whatsapp_user_phone_or_id"
}
```

**Example:**
```json
{
  "session_id": "wa_user_123_20241225",
  "message": "Check my Gmail inbox",
  "user_id": "+1234567890"
}
```

---

## ✅ **Health Check & Testing**

### **1. Health Check**
```bash
GET https://elva-mcp-service.onrender.com/api/mcp/health
```

### **2. Test WhatsApp Message**
```bash
curl -X POST "https://elva-mcp-service.onrender.com/api/mcp?token=kumararpit9468" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_wa_001", 
    "message": "Hello from WhatsApp!",
    "user_id": "test_user"
  }'
```

### **3. Test Gmail Intent**
```bash
curl -X POST "https://elva-mcp-service.onrender.com/api/mcp" \
  -H "Authorization: Bearer kumararpit9468" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_wa_002", 
    "message": "Check my Gmail inbox",
    "user_id": "test_user"
  }'
```

### **4. Test Weather Intent**
```bash
curl -X POST "https://elva-mcp-service.onrender.com/api/mcp" \
  -H "Authorization: Bearer kumararpit9468" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_wa_003", 
    "message": "What's the weather in Delhi tomorrow?",
    "user_id": "test_user"
  }'
```

---

## 🎯 **What This Enables for WhatsApp Users**

1. **General Conversation**: Natural chat with Elva AI
2. **Gmail Integration**: 
   - "Check my Gmail inbox"
   - "Any unread emails?"
   - "Summarize my last 5 emails"
3. **Weather Queries**:
   - "What's the weather in Delhi?"
   - "Will it rain tomorrow?"
   - "Weather forecast for Mumbai"
4. **Session Memory**: Full conversation context maintained
5. **Follow-up Actions**: Email approvals, weather forecasts
6. **Error Handling**: WhatsApp-specific error responses

---

## 🛠 **Production Features**

- **24/7 Uptime**: Deployed on Render with auto-scaling
- **Session Memory**: MongoDB + Redis for persistence
- **Intent Detection**: Gmail, Weather, General Chat
- **Error Handling**: Comprehensive error logging and recovery
- **Security**: Bearer token authentication
- **Monitoring**: Health checks and conversation logging
- **Scalability**: Handles multiple concurrent WhatsApp users

---

## 🔒 **Security & Authentication**

- **Bearer Token**: `kumararpit9468` (configurable via environment)
- **Multiple Auth Methods**: Query parameter or Authorization header
- **Request Validation**: Payload structure validation
- **Error Logging**: Secure error tracking without exposing internals
- **Rate Limiting**: Built-in Render platform protection

---

## 📊 **Monitoring & Logs**

### **Session Management**
```bash
GET https://elva-mcp-service.onrender.com/api/mcp/sessions?token=kumararpit9468
```

### **Health Status**
```bash
GET https://elva-mcp-service.onrender.com/api/mcp/health
```

### **Error Tracking**
- All WhatsApp conversations logged to MongoDB
- Error logs stored for debugging
- Session context maintained in Redis

---

## 🚀 **Next Steps**

1. **Deploy** the updated MCP service to Render
2. **Configure** environment variables in Render dashboard
3. **Test** the connection using the curl commands above
4. **Connect** Puch AI using the `/mcp connect` command
5. **Verify** WhatsApp messages flow through Elva AI pipeline

The system is now ready for production WhatsApp integration with permanent URLs and secure token-based authentication!