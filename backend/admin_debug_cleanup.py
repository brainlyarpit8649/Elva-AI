#!/usr/bin/env python3
"""
Admin Debug Cleanup Script
Removes all admin debug features and code from Elva AI system.
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def cleanup_admin_debug_features():
    """Remove all admin debug features from the codebase"""
    try:
        backend_dir = Path("/app/backend")
        frontend_dir = Path("/app/frontend/src")
        
        # Files to clean
        files_to_clean = []
        
        # Backend files
        files_to_clean.extend([
            backend_dir / "server.py",
            backend_dir / "server_clean.py"
        ])
        
        # Frontend files
        files_to_clean.extend([
            frontend_dir / "ChatBox.js",
            frontend_dir / "App.js"
        ])
        
        for file_path in files_to_clean:
            if file_path.exists():
                clean_file_from_admin_debug(file_path)
        
        logger.info("✅ Admin debug cleanup completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during admin debug cleanup: {e}")
        return False

def clean_file_from_admin_debug(file_path: Path):
    """Clean admin debug code from a specific file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Patterns to remove (admin debug related)
        patterns_to_remove = [
            # Admin debug functions
            r'def format_admin_debug_context\(.*?\n.*?""".*?""".*?\n(?:.*?\n)*?.*?return.*?\n',
            r'@api_router\.get\("/admin/debug/context"\).*?\n(?:.*?\n)*?.*?raise HTTPException.*?\n',
            r'@api_router\.post\("/admin/debug/context"\).*?\n(?:.*?\n)*?.*?raise HTTPException.*?\n',
            
            # Admin email checks
            r'ADMIN_EMAILS = \[.*?\]',
            r'brainlyarpit8649@gmail\.com|kumararpit9468@gmail\.com',
            r'DEBUG_ADMIN_TOKEN',
            
            # Admin debug state variables
            r'const \[isAdminMode.*?\n',
            r'const \[showAdminToggle.*?\n',
            r'const checkAdminEmail.*?\n',
            
            # Admin debug related imports and variables
            r'# Admin.*?\n',
            r'// Admin.*?\n',
            r'isAdminMode|showAdminToggle|adminEmail|checkAdminEmail',
        ]
        
        # Remove admin debug patterns
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        
        # Remove empty lines that might be left behind
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            logger.info(f"✅ Cleaned admin debug code from {file_path}")
        else:
            logger.info(f"ℹ️  No admin debug code found in {file_path}")
            
    except Exception as e:
        logger.error(f"❌ Error cleaning {file_path}: {e}")

def remove_admin_debug_endpoints():
    """Remove admin debug endpoints from server.py"""
    try:
        server_file = Path("/app/backend/server.py")
        if not server_file.exists():
            return False
        
        with open(server_file, 'r') as f:
            lines = f.readlines()
        
        # Find and remove admin debug endpoint blocks
        new_lines = []
        skip_lines = False
        brace_count = 0
        
        for line in lines:
            # Start skipping if we find admin debug endpoint
            if '@api_router.get("/admin/debug/context")' in line or '@api_router.post("/admin/debug/context")' in line:
                skip_lines = True
                brace_count = 0
                continue
            
            # Stop skipping after the function ends
            if skip_lines:
                if 'def ' in line or '@api_router' in line or (line.strip() == '' and brace_count == 0):
                    if 'admin' not in line.lower() and 'debug' not in line.lower():
                        skip_lines = False
                        new_lines.append(line)
                continue
            
            # Remove admin-related lines
            if any(keyword in line for keyword in ['brainlyarpit8649@gmail.com', 'kumararpit9468@gmail.com', 'DEBUG_ADMIN_TOKEN', 'format_admin_debug_context']):
                continue
            
            new_lines.append(line)
        
        # Write cleaned content
        with open(server_file, 'w') as f:
            f.writelines(new_lines)
        
        logger.info("✅ Removed admin debug endpoints from server.py")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error removing admin debug endpoints: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cleanup_admin_debug_features()
    remove_admin_debug_endpoints()