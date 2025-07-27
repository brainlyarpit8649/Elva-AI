#!/usr/bin/env python3
"""
Simple script to toggle Gmail authentication status for testing
"""

import sys
import re

def toggle_gmail_status():
    """Toggle the authenticated status in simple_server.py"""
    try:
        with open('simple_server.py', 'r') as f:
            content = f.read()
        
        # Find current status
        if '"authenticated": False' in content:
            new_content = content.replace('"authenticated": False', '"authenticated": True')
            new_status = "Connected"
        elif '"authenticated": True' in content:
            new_content = content.replace('"authenticated": True', '"authenticated": False')
            new_status = "Disconnected"
        else:
            print("❌ Could not find authentication status in simple_server.py")
            return False
        
        # Write back to file
        with open('simple_server.py', 'w') as f:
            f.write(new_content)
            
        print(f"✅ Gmail status toggled to: {new_status}")
        print("🔄 The backend server will reload automatically if running with --reload")
        return True
        
    except Exception as e:
        print(f"❌ Error toggling status: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("Gmail Status Toggle Script")
        print("Usage: python toggle_status.py")
        print("This script toggles the Gmail authentication status between True and False")
        print("for testing the frontend UI implementation.")
    else:
        toggle_gmail_status()