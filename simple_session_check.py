#!/usr/bin/env python3
"""
Simple way to check your current Elva AI session and MCP storage
"""
import requests
import json

def check_demo_session():
    """Check the demo session we just created"""
    url = "https://329904b0-2cf4-48ba-8d24-e322e324860a.preview.emergentagent.com/api/admin/debug/context"
    params = {
        'session_id': 'session_demo_12345',
        'command': 'show_context'
    }
    headers = {
        'x-debug-token': 'elva-admin-debug-2024-secure'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS: MCP Debug endpoint working!")
            print(f"📊 Session: {data['session_id']}")
            print(f"📝 Context Found: {data['success']}")
            print(f"📄 Formatted Context:")
            print(data['formatted_context'])
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    print("🧠 Testing MCP Debug with Demo Session")
    print("=" * 50)
    check_demo_session()