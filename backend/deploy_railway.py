# Railway deployment script for MCP service
import os
import requests
import json
import subprocess
import time

RAILWAY_API_TOKEN = "3a6f728b-0a66-4d21-92f5-a0db6e52a221"
RAILWAY_API_URL = "https://backboard.railway.app/graphql"

def deploy_to_railway():
    """Deploy MCP service to Railway"""
    
    print("🚀 Starting Railway deployment for MCP service...")
    
    headers = {
        "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Create new project
    create_project_mutation = """
    mutation projectCreate($input: ProjectCreateInput!) {
        projectCreate(input: $input) {
            id
            name
            description
        }
    }
    """
    
    project_data = {
        "query": create_project_mutation,
        "variables": {
            "input": {
                "name": "elva-mcp-service",
                "description": "MCP (Model Context Protocol) Microservice for Elva AI"
            }
        }
    }
    
    try:
        response = requests.post(RAILWAY_API_URL, json=project_data, headers=headers)
        result = response.json()
        
        if "data" in result and result["data"]["projectCreate"]:
            project = result["data"]["projectCreate"]
            project_id = project["id"]
            print(f"✅ Project created: {project['name']} (ID: {project_id})")
            
            # Environment variables to set
            env_vars = {
                "MCP_API_TOKEN": "kumararpit9468",
                "MCP_REDIS_URL": "rediss://default:ARTGAAIjcDFjNWNlOTRjZDY5ODM0YTBjOTI2MTc3NzhmNzg3YzBkNnAxMA@brave-deer-5318.upstash.io:6379",
                "MCP_MONGO_URI": "mongodb+srv://kumararpit9468:kumararpit1234coc@elva-mcp-mongo.uzclf39.mongodb.net/elva_mcp?retryWrites=true&w=majority&appName=elva-mcp-mongo",
                "MCP_DB_NAME": "elva_mcp",
                "PORT": "8002"
            }
            
            print("✅ MCP service deployment initiated successfully!")
            print(f"📋 Project ID: {project_id}")
            print("🔧 Next steps:")
            print("1. Connect your GitHub repository to Railway")
            print("2. Set the environment variables")
            print("3. Deploy the service")
            
            return project_id
            
        else:
            print(f"❌ Failed to create project: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Railway deployment failed: {e}")
        return None

if __name__ == "__main__":
    deploy_to_railway()