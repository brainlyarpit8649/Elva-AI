from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Elva AI Test Server Running"}

@app.get("/api/gmail/status")
def gmail_status(session_id: str = None):
    """Gmail status endpoint for testing"""
    print(f"📧 Gmail status check for session: {session_id}")
    
    response = {
        "success": True,
        "authenticated": False,  # Toggle this to test different states
        "credentials_configured": True,
        "requires_auth": True,
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
        "service": "gmail",
        "session_id": session_id,
        "error": None
    }
    
    print(f"📊 Response: {response}")
    return response

@app.get("/api/gmail/auth")
def gmail_auth(session_id: str = None):
    """Gmail auth endpoint for testing"""
    return {
        "success": True,
        "auth_url": f"https://accounts.google.com/oauth2/auth?session_id={session_id}",
        "message": "Mock auth URL"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Gmail Test Server on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)