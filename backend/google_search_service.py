# Enhanced Google Search API Service
# Replaces Playwright-based web search with clean, API-driven results

import os
import json
import httpx
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class GoogleSearchService:
    """Google Search API service for clean, structured web search results"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.cse_id = os.getenv("GOOGLE_CSE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        if not self.api_key or not self.cse_id:
            logger.warning("⚠️ Google Search API credentials not configured")
    
    async def search_web(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform web search using Google Search API
        Returns clean, formatted results for chat display
        """
        try:
            if not self.api_key or not self.cse_id:
                return {
                    "success": False,
                    "error": "Google Search API not configured",
                    "formatted_results": "❌ **Search Configuration Error**\n\nGoogle Search API credentials are not configured. Please contact support.",
                    "raw_results": []
                }
            
            logger.info(f"🔍 Performing Google Search: {query}")
            start_time = datetime.now()
            
            # Make API request to Google Custom Search
            params = {
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "num": min(max_results, 10),  # Google API max is 10
                "safe": "active",
                "fields": "items(title,link,snippet,displayLink)"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                search_data = response.json()
                items = search_data.get("items", [])
                
                if not items:
                    return {
                        "success": True,
                        "query": query,
                        "count": 0,
                        "formatted_results": f"🔍 **No results found for:** {query}\n\nTry rephrasing your search query or using different keywords.",
                        "raw_results": [],
                        "execution_time": (datetime.now() - start_time).total_seconds()
                    }
                
                # Format results for clean chat display
                formatted_results = self._format_search_results(query, items)
                
                # Structure raw results for potential n8n forwarding
                raw_results = []
                for item in items:
                    raw_results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "domain": item.get("displayLink", "")
                    })
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    "success": True,
                    "query": query,
                    "count": len(items),
                    "formatted_results": formatted_results,
                    "raw_results": raw_results,
                    "execution_time": execution_time
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Google Search API error: {e.response.status_code} - {e.response.text}")
            error_msg = self._format_api_error(e.response.status_code, query)
            return {
                "success": False,
                "error": f"API Error: {e.response.status_code}",
                "formatted_results": error_msg,
                "raw_results": []
            }
            
        except Exception as e:
            logger.error(f"❌ Search service error: {e}")
            return {
                "success": False,
                "error": str(e),
                "formatted_results": f"❌ **Search Error**\n\nUnable to perform search for: {query}\n\nError: {str(e)}",
                "raw_results": []
            }
    
    def _format_search_results(self, query: str, items: List[Dict]) -> str:
        """Format search results for clean chat display"""
        
        result_text = f"🔎 **Web Search Results for:** {query}\n\n"
        
        for i, item in enumerate(items, 1):
            title = item.get("title", "No title")
            link = item.get("link", "")
            snippet = item.get("snippet", "No description available")
            domain = item.get("displayLink", "")
            
            # Clean up snippet (remove excessive whitespace, truncate if too long)
            snippet = " ".join(snippet.split())
            if len(snippet) > 150:
                snippet = snippet[:147] + "..."
            
            result_text += f"{i}️⃣ **{title}**\n"
            result_text += f"🌐 {link}\n"
            result_text += f"📌 {snippet}\n"
            if domain:
                result_text += f"🏠 {domain}\n"
            result_text += "\n"
        
        result_text += f"✨ Found {len(items)} results in total."
        return result_text
    
    def _format_api_error(self, status_code: int, query: str) -> str:
        """Format API error messages for user display"""
        
        if status_code == 400:
            return f"❌ **Search Request Error**\n\nInvalid search query: {query}\n\nPlease try rephrasing your search."
        elif status_code == 403:
            return f"❌ **API Quota Exceeded**\n\nDaily search limit reached for Google Search API.\n\nPlease try again tomorrow or contact support."
        elif status_code == 429:
            return f"❌ **Rate Limit Exceeded**\n\nToo many search requests. Please wait a moment and try again."
        else:
            return f"❌ **Search Service Error**\n\nUnable to perform search for: {query}\n\nError code: {status_code}"
    
    async def search_trends(self, topic: str) -> Dict[str, Any]:
        """
        Search for trending topics related to a specific subject
        """
        trending_queries = [
            f"{topic} trends 2025",
            f"latest {topic} news",
            f"{topic} innovations 2025"
        ]
        
        all_results = []
        formatted_output = f"📈 **Trending Topics for:** {topic}\n\n"
        
        for query in trending_queries[:2]:  # Limit to 2 queries to save API calls
            result = await self.search_web(query, max_results=3)
            if result["success"]:
                all_results.extend(result["raw_results"])
        
        # Format trending results
        if all_results:
            unique_results = []
            seen_domains = set()
            
            for result in all_results:
                domain = result.get("domain", "")
                if domain not in seen_domains:
                    unique_results.append(result)
                    seen_domains.add(domain)
                    
            for i, result in enumerate(unique_results[:5], 1):
                formatted_output += f"{i}️⃣ **{result['title']}**\n"
                formatted_output += f"🌐 {result['link']}\n" 
                formatted_output += f"📌 {result['snippet']}\n\n"
                
            formatted_output += f"✨ Found {len(unique_results)} trending sources."
        else:
            formatted_output += f"❌ No trending information found for: {topic}"
        
        return {
            "success": len(all_results) > 0,
            "topic": topic,
            "formatted_results": formatted_output,
            "raw_results": all_results
        }

# Global Google Search service instance
google_search_service = GoogleSearchService()