#!/usr/bin/env python3
"""
Debug Connection Test Method
Find exactly why _test_connection is failing
"""

import sys
import os
import asyncio
from datetime import datetime

# Add backend directory to path
sys.path.append('/app/backend')

async def debug_connection_test():
    """Debug _test_connection method"""
    print("🔍 Debugging _test_connection Method")
    print("=" * 50)
    
    try:
        from enhanced_message_memory import EnhancedMessageMemory
        
        memory = EnhancedMessageMemory()
        
        # Test the database connection directly
        print("1️⃣ Testing database connection directly...")
        try:
            result = await memory.db.admin.command('ping')
            print(f"   ✅ Direct db.admin.command('ping') successful: {result}")
        except Exception as e:
            print(f"   ❌ Direct db.admin.command('ping') failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test with asyncio.wait_for (like in _test_connection)
        print("\n2️⃣ Testing with asyncio.wait_for (5s timeout)...")
        try:
            result = await asyncio.wait_for(memory.db.admin.command('ping'), timeout=5.0)
            print(f"   ✅ asyncio.wait_for ping successful: {result}")
        except asyncio.TimeoutError:
            print("   ❌ asyncio.wait_for ping timed out after 5 seconds")
        except Exception as e:
            print(f"   ❌ asyncio.wait_for ping failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test the actual _test_connection method
        print("\n3️⃣ Testing actual _test_connection method...")
        try:
            # Reset the connection tested flag
            memory._connection_tested = False
            
            result = await memory._test_connection()
            print(f"   📊 _test_connection result: {result}")
            print(f"   📊 _connection_tested flag: {memory._connection_tested}")
        except Exception as e:
            print(f"   ❌ _test_connection method failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test with longer timeout
        print("\n4️⃣ Testing with longer timeout (15s)...")
        try:
            result = await asyncio.wait_for(memory.db.admin.command('ping'), timeout=15.0)
            print(f"   ✅ Long timeout ping successful: {result}")
        except asyncio.TimeoutError:
            print("   ❌ Long timeout ping timed out after 15 seconds")
        except Exception as e:
            print(f"   ❌ Long timeout ping failed: {e}")
        
        # Test MongoDB client status
        print("\n5️⃣ Testing MongoDB client status...")
        try:
            # Check if client is properly initialized
            print(f"   📊 MongoDB client: {memory.mongo_client}")
            print(f"   📊 Database: {memory.db}")
            print(f"   📊 Collection: {memory.messages_collection}")
            
            # Test server info
            server_info = await memory.db.admin.command('serverStatus')
            print(f"   ✅ Server status retrieved: {server_info.get('host', 'unknown')}")
            
        except Exception as e:
            print(f"   ❌ MongoDB client status check failed: {e}")
        
        print("\n✅ Connection Test Debug Completed!")
        
    except Exception as e:
        print(f"❌ Critical error during connection test debug: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await debug_connection_test()

if __name__ == "__main__":
    asyncio.run(main())