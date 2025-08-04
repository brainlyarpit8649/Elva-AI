# 🔧 MCP Debug Commands - How to See Your Stored Messages

## Method 1: Via Chat Interface (EASIEST)
Just type these commands in your Elva AI chat:

```
show my context
```
or
```  
show context for session <session_id>
```

**Admin emails that can use this**: 
- brainlyarpit8649@gmail.com
- kumararpit9468@gmail.com

## Method 2: Direct API Call
```bash
curl -X GET "https://31274c15-fd00-4c3b-bace-e8891cc7016e.preview.emergentagent.com/api/admin/debug/context?session_id=YOUR_SESSION_ID&command=show_context" \
  -H "x-debug-token: elva-admin-debug-2024-secure"
```

## Method 3: Check Any Session ID
Replace `YOUR_SESSION_ID` with your actual chat session ID:

```bash
curl -s "https://elva-mcp-service.onrender.com/context/read/YOUR_SESSION_ID" \
  -H "Authorization: Bearer kumararpit9468" | jq '.'
```

## Method 4: Use Our Script
```bash
cd /app
python check_mcp.py YOUR_SESSION_ID
```

## How to Find Your Session ID?
- Look in browser developer tools -> Network tab
- Check localStorage in browser console: `localStorage.getItem('sessionId')`
- It's usually visible in the URL or API calls

## What You'll See:
- ✅ All your messages to Elva AI
- ✅ All AI responses  
- ✅ Intent detection results
- ✅ Agent execution results
- ✅ Timestamps and metadata
- ✅ SuperAGI task results (if any)

## Debug Token (Already in .env):
`DEBUG_ADMIN_TOKEN=elva-admin-debug-2024-secure`