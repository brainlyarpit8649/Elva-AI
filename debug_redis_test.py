#!/usr/bin/env python3
"""
Debug Redis Connection in Enhanced Memory System
"""

import sys
import os
import asyncio
import redis
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append('/app/backend')

async def debug_redis_connection():
    """Debug Redis connection specifically"""
    print("🔍 Debugging Redis Connection in Enhanced Memory System")
    print("=" * 60)
    
    load_dotenv('/app/backend/.env')
    
    # Test 1: Direct Redis connection (like we did before)
    print("1️⃣ Testing Direct Redis Connection...")
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        print(f"   Redis URL: {redis_url[:50]}...")
        
        client = redis.from_url(redis_url, socket_connect_timeout=5)
        client.ping()
        print("   ✅ Direct Redis connection successful")
    except Exception as e:
        print(f"   ❌ Direct Redis connection failed: {e}")
        return
    
    # Test 2: Redis connection with enhanced memory system parameters
    print("\n2️⃣ Testing Redis with Enhanced Memory Parameters...")
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        
        # Use exact same parameters as enhanced memory system
        client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
            retry_on_timeout=True,
            socket_connect_timeout=5
        )
        
        # Test connection
        client.ping()
        print("   ✅ Redis connection with enhanced memory parameters successful")
        
        # Test some operations
        client.set("test_key", "test_value", ex=60)
        value = client.get("test_key")
        print(f"   ✅ Redis set/get test successful: {value}")
        
    except Exception as e:
        print(f"   ❌ Redis connection with enhanced memory parameters failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test the enhanced memory system Redis initialization directly
    print("\n3️⃣ Testing Enhanced Memory System Redis Initialization...")
    try:
        from enhanced_message_memory import EnhancedMessageMemory
        
        memory = EnhancedMessageMemory()
        
        # Manually call the Redis initialization with debug
        print("   Calling _initialize_redis()...")
        await memory._initialize_redis()
        
        print(f"   Redis connected: {memory.redis_connected}")
        print(f"   Redis initialized: {memory._redis_initialized}")
        
        if memory.redis_client:
            print("   ✅ Redis client created")
            # Test the client
            try:
                # Use asyncio executor for sync Redis operations
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, memory.redis_client.ping)
                print("   ✅ Redis client ping successful")
            except Exception as ping_error:
                print(f"   ❌ Redis client ping failed: {ping_error}")
        else:
            print("   ❌ Redis client not created")
            
    except Exception as e:
        print(f"   ❌ Enhanced Memory Redis initialization failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await debug_redis_connection()

if __name__ == "__main__":
    asyncio.run(main())