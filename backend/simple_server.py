from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Dict, Any

app = FastAPI(title="Elva AI Backend", description="Simple backend for testing Gmail status")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Elva AI Backend is running"}

@app.get("/api/gmail/status")
async def gmail_status(session_id: str = None) -> Dict[str, Any]:
    """
    Gmail authentication status endpoint for testing
    Returns mock data for demonstration purposes
    """
    print(f"🔍 Gmail status check for session: {session_id}")
    
    # Mock response - you can change authenticated to True to test the connected state
    mock_response = {
        "success": True,
        "authenticated": False,  # Change this to True to test the connected badge
        "credentials_configured": True,
        "requires_auth": True,
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"],
        "service": "gmail",
        "session_id": session_id,
        "error": None
    }
    
    print(f"📊 Returning Gmail status: {mock_response}")
    return mock_response

@app.get("/api/gmail/auth")
async def gmail_auth(session_id: str = None):
    """
    Gmail authentication initiation endpoint for testing
    """
    print(f"🔐 Gmail auth requested for session: {session_id}")
    
    return {
        "success": True,
        "auth_url": f"https://accounts.google.com/oauth2/auth?mock=true&session_id={session_id}",
        "message": "Mock OAuth2 URL generated"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "elva-ai-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)