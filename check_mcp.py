#!/usr/bin/env python3
"""
Simple script to check what's stored in MCP for any session
"""
import httpx
import json
import asyncio
import sys

MCP_URL = "https://elva-mcp-service.onrender.com"
MCP_TOKEN = "kumararpit9468"

async def check_mcp_context(session_id):
    """Check what's stored in MCP for a session"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Read context from MCP
            response = await client.get(
                f"{MCP_URL}/context/read/{session_id}",
                headers={"Authorization": f"Bearer {MCP_TOKEN}"}
            )
            
            print(f"🔍 Checking MCP storage for session: {session_id}")
            print(f"📡 MCP URL: {MCP_URL}")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS: Found data in MCP!")
                print(f"📝 Total Messages Stored: {len(data.get('data', {}).get('appends', []))}")
                
                # Show message summary
                appends = data.get('data', {}).get('appends', [])
                if appends:
                    print(f"\n📨 MESSAGE HISTORY:")
                    for i, msg in enumerate(appends[:5]):  # Show first 5
                        timestamp = msg.get('timestamp', 'No timestamp')
                        intent = msg.get('intent', 'unknown')
                        output = msg.get('output', {})
                        user_msg = output.get('user_message', 'N/A')[:50]
                        ai_response = output.get('ai_response', 'N/A')[:50]
                        
                        print(f"  {i+1}. [{timestamp[:19]}] Intent: {intent}")
                        print(f"     User: {user_msg}...")
                        print(f"     AI: {ai_response}...")
                        print()
                
                # Show raw JSON for debugging
                print(f"\n🔧 RAW DATA:")
                print(json.dumps(data, indent=2)[:1000] + "..." if len(str(data)) > 1000 else json.dumps(data, indent=2))
                
            elif response.status_code == 404:
                print(f"❌ No data found for session: {session_id}")
                print("💡 This session hasn't sent any messages yet")
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error connecting to MCP: {e}")

async def list_all_sessions():
    """List all available sessions in MCP"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{MCP_URL}/contexts/list",
                headers={"Authorization": f"Bearer {MCP_TOKEN}"}
            )
            
            print(f"📋 Listing all sessions in MCP:")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                sessions = data.get('sessions', [])
                print(f"✅ Found {len(sessions)} sessions:")
                
                for session in sessions:
                    session_id = session.get('session_id', 'Unknown')
                    message_count = session.get('message_count', 0)
                    last_updated = session.get('last_updated', 'Unknown')
                    print(f"  📁 Session: {session_id}")
                    print(f"     Messages: {message_count}")
                    print(f"     Last Updated: {last_updated}")
                    print()
                    
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error connecting to MCP: {e}")

async def main():
    print("🧠 MCP (Model Context Protocol) Storage Checker")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python check_mcp.py <session_id>     - Check specific session")
        print("  python check_mcp.py list             - List all sessions")
        print("  python check_mcp.py test123          - Check session 'test123'")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        await list_all_sessions()
    else:
        await check_mcp_context(command)

if __name__ == "__main__":
    asyncio.run(main())