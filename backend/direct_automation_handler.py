import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from playwright_service import playwright_service

# Import weather service functions
from weather_service_tomorrow import (
    get_current_weather, 
    get_weather_forecast,
    get_air_quality_index, 
    get_weather_alerts,
    get_sun_times
)

logger = logging.getLogger(__name__)

class DirectAutomationHandler:
    """
    Handler for direct automation intents that bypass AI response generation
    and modal approval, providing immediate automation results
    """
    
    def __init__(self):
        self.automation_templates = {
            "web_search": {
                "success_template": "{search_results}",  # Google Search service already formats the results
                "error_template": "❌ Unable to perform web search: {error}",
                "automation_type": "google_search"
            },
            "check_linkedin_notifications": {
                "success_template": "🔔 **LinkedIn Notifications** ({count} new)\n{notifications}",
                "error_template": "❌ Unable to check LinkedIn notifications: {error}",
                "automation_type": "linkedin_insights"
            },
            "check_gmail_inbox": {
                "success_template": "📧 **Gmail Inbox** ({count} emails)\n{emails}",
                "error_template": "❌ Unable to check Gmail inbox: {error}",
                "automation_type": "gmail_automation"
            },
            "check_gmail_unread": {
                "success_template": "📧 **Gmail Unread** ({count} unread emails)\n{emails}",
                "error_template": "❌ Unable to check Gmail unread emails: {error}",
                "automation_type": "gmail_automation"
            },
            "email_inbox_check": {
                "success_template": "📥 **Your Inbox** ({count} unread emails)\n{emails}",
                "error_template": "❌ Unable to check your inbox: {error}",
                "automation_type": "gmail_automation"
            },
            # Enhanced Gmail intents
            "summarize_gmail_emails": {
                "success_template": "📧 **Email Summary** ({count} emails processed)\n{summary}",
                "error_template": "❌ Unable to summarize emails: {error}",
                "automation_type": "enhanced_gmail_automation"
            },
            "search_gmail_emails": {
                "success_template": "🔍 **Gmail Search Results** ({count} emails found)\n{search_results}",
                "error_template": "❌ Unable to search emails: {error}",
                "automation_type": "enhanced_gmail_automation"
            },
            "categorize_gmail_emails": {
                "success_template": "📊 **Email Categories** ({count} emails categorized)\n{categories}",
                "error_template": "❌ Unable to categorize emails: {error}",
                "automation_type": "enhanced_gmail_automation"
            },
            "scrape_product_listings": {
                "success_template": "🛒 **Product Listings** ({count} found)\n{listings}",
                "error_template": "❌ Unable to scrape product listings: {error}",
                "automation_type": "data_extraction"
            },
            "linkedin_job_alerts": {
                "success_template": "💼 **Job Alerts** ({count} new opportunities)\n{jobs}",
                "error_template": "❌ Unable to check job alerts: {error}",
                "automation_type": "linkedin_insights"
            },
            "check_website_updates": {
                "success_template": "🔍 **Website Updates**\n📝 **{website}**: {changes}",
                "error_template": "❌ Unable to check website updates: {error}",
                "automation_type": "web_scraping"
            },
            "monitor_competitors": {
                "success_template": "📊 **Competitor Analysis**\n🏢 **{company}**: {insights}",
                "error_template": "❌ Unable to monitor competitor data: {error}",
                "automation_type": "data_extraction"
            },
            "scrape_news_articles": {
                "success_template": "📰 **Latest News** ({count} articles)\n{articles}",
                "error_template": "❌ Unable to scrape news articles: {error}",
                "automation_type": "web_scraping"
            },
            # Weather intents using Tomorrow.io API
            "get_current_weather": {
                "success_template": "🌤️ **Current Weather Update**\n\nHere's what it's like right now:\n{weather_data}",
                "error_template": "❌ Oops! I couldn't get the weather data right now: {error}",
                "automation_type": "weather_api"
            },
            "get_weather_forecast": {
                "success_template": "🌦️ **Weather Forecast**\n\nHere's what to expect:\n{weather_data}",
                "error_template": "❌ Sorry, I couldn't fetch the weather forecast: {error}",
                "automation_type": "weather_api"
            },
            "get_air_quality_index": {
                "success_template": "💨 **Air Quality Report**\n\nHere's the current air quality info:\n{weather_data}",
                "error_template": "❌ I couldn't get air quality data right now: {error}",
                "automation_type": "weather_api"
            },
            "get_weather_alerts": {
                "success_template": "🚨 **Weather Alerts**\n\nHere are any active weather warnings:\n{weather_data}",
                "error_template": "❌ I couldn't check for weather alerts: {error}",
                "automation_type": "weather_api"
            },
            "get_sun_times": {
                "success_template": "🌅 **Sunrise & Sunset Times**\n\nHere's today's sun schedule:\n{weather_data}",
                "error_template": "❌ I couldn't get sunrise/sunset times: {error}",
                "automation_type": "weather_api"
            }
        }
    
    async def process_direct_automation(self, intent_data: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """
        Process direct automation intent and return formatted result
        
        Args:
            intent_data: Intent data from AI detection
            session_id: Session ID for authentication
            
        Returns:
            Dict containing automation result and formatting info
        """
        intent = intent_data.get("intent")
        template_info = self.automation_templates.get(intent)
        
        if not template_info:
            return {
                "success": False,
                "message": f"❌ Unknown automation intent: {intent}",
                "execution_time": 0,
                "data": {}
            }
        
        logger.info(f"🤖 Processing direct automation: {intent} for session: {session_id}")
        start_time = datetime.now()
        
        try:
            # Route to appropriate automation handler
            automation_type = template_info["automation_type"]
            
            if automation_type == "google_search":
                result = await self._handle_google_search(intent, intent_data)
            elif automation_type == "linkedin_insights":
                result = await self._handle_linkedin_automation(intent, intent_data)
            elif automation_type == "gmail_automation":
                result = await self._handle_gmail_automation(intent, intent_data, session_id)
            elif automation_type == "enhanced_gmail_automation":
                result = await self._handle_enhanced_gmail_automation(intent, intent_data, session_id)
            elif automation_type == "weather_api":
                result = await self._handle_weather_automation(intent, intent_data)
            elif automation_type == "data_extraction":
                result = await self._handle_data_extraction(intent, intent_data)
            elif automation_type == "web_scraping":
                result = await self._handle_web_scraping(intent, intent_data)
            else:
                result = {"success": False, "data": {}, "message": "Unknown automation type"}
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Format result using template
            if result["success"]:
                formatted_message = self._format_success_result(intent, result["data"], template_info)
            else:
                formatted_message = template_info["error_template"].format(
                    error=result.get("message", "Unknown error"),
                    **intent_data
                )
            
            return {
                "success": result["success"],
                "message": formatted_message,
                "execution_time": execution_time,
                "data": result["data"],
                "automation_intent": intent
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Direct automation error for {intent}: {e}")
            
            error_message = template_info["error_template"].format(
                error=str(e),
                **intent_data
            )
            
            return {
                "success": False,
                "message": error_message,
                "execution_time": execution_time,
                "data": {},
                "automation_intent": intent
            }
    
    async def _handle_google_search(self, intent: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google Search automation using Google Search API"""
        try:
            from google_search_service import google_search_service
            
            # Extract search query from intent data
            search_query = intent_data.get("query", "")
            
            if not search_query:
                return {
                    "success": False,
                    "data": {},
                    "message": "No search query provided"
                }
            
            logger.info(f"🔍 Performing Google Search for: {search_query}")
            
            # Use Google Search API service
            search_result = await google_search_service.search_web(search_query, max_results=5)
            
            if search_result["success"]:
                return {
                    "success": True,
                    "data": {
                        "search_results": search_result["formatted_results"],
                        "query": search_query,
                        "count": search_result["count"],
                        "raw_results": search_result["raw_results"]
                    },
                    "message": f"Found {search_result['count']} search results"
                }
            else:
                return {
                    "success": False,
                    "data": {"search_results": search_result["formatted_results"]},
                    "message": search_result.get("error", "Search failed")
                }
                
        except Exception as e:
            logger.error(f"Google Search automation error: {e}")
            return {
                "success": False,
                "data": {},
                "message": f"Search service error: {str(e)}"
            }
    
    async def _handle_gmail_automation(self, intent: str, intent_data: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """Handle Gmail automation using Gmail API"""
        # Import Gmail OAuth service from server.py global instance
        from server import gmail_oauth_service
        
        try:
            # Get the user email from intent_data, fallback to known email
            user_email = intent_data.get("user_email", "brainlyarpit8649@gmail.com")
            session_id = session_id or intent_data.get("session_id", "default_session")
            logger.info(f"🔍 Gmail API automation for user: {user_email}, session: {session_id}")
            logger.info(f"🔍 Intent data: {intent_data}")
            
            if intent in ["check_gmail_inbox", "check_gmail_unread", "email_inbox_check"]:
                # Use real Gmail API service
                try:
                    # Determine query based on intent
                    query = 'is:unread' if intent in ["check_gmail_unread", "email_inbox_check"] else 'in:inbox'
                    max_results = intent_data.get("max_results", 10)
                    
                    gmail_result = await gmail_oauth_service.check_inbox(
                        session_id=session_id,
                        max_results=max_results,
                        query=query
                    )
                    
                    if gmail_result['success']:
                        emails_data = gmail_result['data']['emails']
                        
                        # Transform Gmail API response to our format
                        formatted_emails = []
                        for email in emails_data:
                            formatted_emails.append({
                                "id": email.get("id"),
                                "sender": email.get("from", "Unknown"),
                                "subject": email.get("subject", "No Subject"),
                                "snippet": email.get("snippet", ""),
                                "date": email.get("date", "Unknown Date"),
                                "unread": True if intent in ["check_gmail_unread", "email_inbox_check"] else 'UNREAD' in email.get("labels", [])
                            })
                        
                        return {
                            "success": True,
                            "data": {
                                "count": len(formatted_emails),
                                "emails": formatted_emails,
                                "user_email": user_email,
                                "query_used": query,
                                "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            },
                            "message": f"Successfully retrieved {len(formatted_emails)} emails from Gmail API"
                        }
                    else:
                        # Handle authentication required
                        if gmail_result.get('requires_auth', False):
                            return {
                                "success": False,
                                "data": {"count": 0, "emails": [], "requires_auth": True},
                                "message": "🔐 Please connect your Gmail account to let Elva AI access your inbox.\n\n👉 Click the 'Connect Gmail' button to continue."
                            }
                        else:
                            logger.error(f"❌ Gmail API failed: {gmail_result['message']}")
                            return {
                                "success": False,
                                "data": {"count": 0, "emails": []},
                                "message": f"❌ Gmail API error: {gmail_result['message']}"
                            }
                        
                except Exception as e:
                    logger.error(f"❌ Gmail API automation error: {e}")
                    return {
                        "success": False,
                        "data": {"count": 0, "emails": []},
                        "message": f"❌ Gmail API error: {str(e)}"
                    }
            
            return {"success": False, "data": {}, "message": "Gmail automation not implemented"}
            
        except Exception as e:
            logger.error(f"Gmail automation handler error: {e}")
            return {"success": False, "data": {}, "message": str(e)}

    async def _handle_enhanced_gmail_automation(self, intent: str, intent_data: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """Handle enhanced Gmail automation with summarization, search, and categorization"""
        from server import gmail_oauth_service
        from superagi_client import superagi_client  # Import SuperAGI for email processing
        
        try:
            session_id = session_id or intent_data.get("session_id", "default_session")
            logger.info(f"🧠 Enhanced Gmail automation: {intent} for session: {session_id}")
            
            if intent == "summarize_gmail_emails":
                # Extract parameters for email summarization
                count = intent_data.get("count", 5)  # Default to 5 emails
                time_filter = intent_data.get("time_filter", "latest")
                include_unread_only = intent_data.get("include_unread_only", False)
                
                # Build Gmail query based on parameters
                if include_unread_only:
                    query = 'is:unread'
                elif time_filter == "today":
                    query = 'newer_than:1d'
                elif time_filter == "recent":
                    query = 'newer_than:3d'
                else:  # latest
                    query = 'in:inbox'
                
                # Fetch emails from Gmail
                gmail_result = await gmail_oauth_service.check_inbox(
                    session_id=session_id,
                    max_results=count,
                    query=query
                )
                
                if not gmail_result['success']:
                    if gmail_result.get('requires_auth', False):
                        return {
                            "success": False,
                            "data": {"count": 0, "summary": "", "requires_auth": True},
                            "message": "🔐 Please connect your Gmail account to let Elva AI summarize your emails.\n\n👉 Click the 'Connect Gmail' button to continue."
                        }
                    else:
                        return {
                            "success": False,
                            "data": {"count": 0, "summary": ""},
                            "message": f"❌ Gmail API error: {gmail_result['message']}"
                        }
                
                emails_data = gmail_result['data']['emails']
                
                if not emails_data:
                    return {
                        "success": True,
                        "data": {
                            "count": 0,
                            "summary": f"📭 No {'unread ' if include_unread_only else ''}emails found for the specified criteria."
                        },
                        "message": "No emails to summarize"
                    }
                
                # Use SuperAGI email agent for intelligent summarization
                try:
                    # Write email context to MCP for SuperAGI processing
                    from mcp_integration import get_mcp_service
                    mcp_service = get_mcp_service()
                    
                    context_data = {
                        "emails": emails_data,
                        "summary_request": {
                            "count": count,
                            "time_filter": time_filter,
                            "include_unread_only": include_unread_only,
                            "user_request": f"Summarize {count} {'unread ' if include_unread_only else ''}{time_filter} emails"
                        }
                    }
                    
                    await mcp_service.write_context(
                        session_id=session_id,
                        intent="email_summarization",
                        data=context_data
                    )
                    
                    # Execute SuperAGI email agent for summarization
                    goal = f"Summarize the {count} {'unread ' if include_unread_only else ''}{time_filter} emails and provide key insights, priority actions, and important themes. Focus on actionable information."
                    
                    superagi_result = await superagi_client.run_task(
                        session_id=session_id,
                        goal=goal,
                        agent_type="email_agent"
                    )
                    
                    if superagi_result.get("success"):
                        summary_text = superagi_result.get("email_summary", "")
                        key_insights = superagi_result.get("key_insights", [])
                        suggested_actions = superagi_result.get("suggested_actions", [])
                        
                        # Format the summary with proper structure
                        formatted_summary = f"📧 **Email Summary ({count} emails analyzed)**\n\n"
                        formatted_summary += f"📝 **Overview:**\n{summary_text}\n\n"
                        
                        if key_insights:
                            formatted_summary += f"💡 **Key Insights:**\n"
                            for insight in key_insights:
                                formatted_summary += f"• {insight}\n"
                            formatted_summary += "\n"
                        
                        if suggested_actions:
                            formatted_summary += f"🎯 **Suggested Actions:**\n"
                            for action in suggested_actions:
                                formatted_summary += f"• {action}\n"
                        
                        return {
                            "success": True,
                            "data": {
                                "count": len(emails_data),
                                "summary": formatted_summary,
                                "key_insights": key_insights,
                                "suggested_actions": suggested_actions,
                                "time_filter": time_filter,
                                "include_unread_only": include_unread_only
                            },
                            "message": f"Successfully summarized {len(emails_data)} emails"
                        }
                    else:
                        # Fallback to basic summarization
                        return await self._basic_email_summarization(emails_data, count, time_filter, include_unread_only)
                        
                except Exception as superagi_error:
                    logger.error(f"SuperAGI email summarization error: {superagi_error}")
                    # Fallback to basic summarization
                    return await self._basic_email_summarization(emails_data, count, time_filter, include_unread_only)
            
            elif intent == "search_gmail_emails":
                # Extract search parameters
                sender = intent_data.get("sender", "")
                keywords = intent_data.get("keywords", [])
                search_query = intent_data.get("search_query", "")
                max_results = intent_data.get("max_results", 10)
                time_filter = intent_data.get("time_filter", "")
                has_attachment = intent_data.get("has_attachment", False)
                
                # Build comprehensive Gmail search query
                if not search_query:
                    query_parts = []
                    if sender:
                        query_parts.append(f"from:{sender}")
                    if keywords:
                        query_parts.extend(keywords)
                    if has_attachment:
                        query_parts.append("has:attachment")
                    if time_filter == "last_week":
                        query_parts.append("newer_than:7d")
                    elif time_filter == "today":
                        query_parts.append("newer_than:1d")
                    
                    search_query = " ".join(query_parts)
                
                if not search_query:
                    return {
                        "success": False,
                        "data": {"count": 0, "search_results": []},
                        "message": "❌ No search criteria specified"
                    }
                
                # Search Gmail with the constructed query
                gmail_result = await gmail_oauth_service.check_inbox(
                    session_id=session_id,
                    max_results=max_results,
                    query=search_query
                )
                
                if not gmail_result['success']:
                    if gmail_result.get('requires_auth', False):
                        return {
                            "success": False,
                            "data": {"count": 0, "search_results": [], "requires_auth": True},
                            "message": "🔐 Please connect your Gmail account to search your emails.\n\n👉 Click the 'Connect Gmail' button to continue."
                        }
                    else:
                        return {
                            "success": False,
                            "data": {"count": 0, "search_results": []},
                            "message": f"❌ Gmail search error: {gmail_result['message']}"
                        }
                
                emails_data = gmail_result['data']['emails']
                
                # Format search results
                if not emails_data:
                    return {
                        "success": True,
                        "data": {
                            "count": 0,
                            "search_results": f"🔍 No emails found matching your search criteria: '{search_query}'"
                        },
                        "message": "No emails found"
                    }
                
                formatted_results = f"🔍 **Search Results for:** '{search_query}'\n\n"
                for i, email in enumerate(emails_data, 1):
                    sender = email.get('from', 'Unknown')
                    if '<' in sender and '>' in sender:
                        sender_name = sender.split('<')[0].strip().strip('"')
                    else:
                        sender_name = sender
                    
                    subject = email.get('subject', 'No Subject')
                    date_str = email.get('date', 'Unknown Date')
                    snippet = email.get('snippet', '')
                    
                    if len(snippet) > 80:
                        snippet = snippet[:77] + '...'
                    
                    formatted_results += f"**{i}.** 👤 **{sender_name}**\n"
                    formatted_results += f"   📧 **Subject:** {subject}\n"
                    formatted_results += f"   📅 **Date:** {date_str}\n"
                    formatted_results += f"   💬 **Preview:** {snippet or 'No preview available'}\n\n"
                
                return {
                    "success": True,
                    "data": {
                        "count": len(emails_data),
                        "search_results": formatted_results,
                        "search_query": search_query,
                        "emails": emails_data
                    },
                    "message": f"Found {len(emails_data)} emails matching your search"
                }
            
            elif intent == "categorize_gmail_emails":
                # Extract categorization parameters
                count = intent_data.get("count", 20)
                categories = intent_data.get("categories", ["work", "personal", "promotions", "social", "important"])
                focus_categories = intent_data.get("focus_categories", categories)
                time_filter = intent_data.get("time_filter", "recent")
                
                # Build query for recent emails
                if time_filter == "today":
                    query = 'newer_than:1d'
                elif time_filter == "recent":
                    query = 'newer_than:3d'
                else:
                    query = 'in:inbox'
                
                # Fetch emails for categorization
                gmail_result = await gmail_oauth_service.check_inbox(
                    session_id=session_id,
                    max_results=count,
                    query=query
                )
                
                if not gmail_result['success']:
                    if gmail_result.get('requires_auth', False):
                        return {
                            "success": False,
                            "data": {"count": 0, "categories": {}, "requires_auth": True},
                            "message": "🔐 Please connect your Gmail account to categorize your emails.\n\n👉 Click the 'Connect Gmail' button to continue."
                        }
                    else:
                        return {
                            "success": False,
                            "data": {"count": 0, "categories": {}},
                            "message": f"❌ Gmail categorization error: {gmail_result['message']}"
                        }
                
                emails_data = gmail_result['data']['emails']
                
                if not emails_data:
                    return {
                        "success": True,
                        "data": {
                            "count": 0,
                            "categories": "📭 No emails found for categorization."
                        },
                        "message": "No emails to categorize"
                    }
                
                # Use AI-powered categorization
                categorized_emails = await self._categorize_emails_with_ai(emails_data, categories)
                
                # Format categorization results
                formatted_categories = f"📊 **Email Categories** ({len(emails_data)} emails analyzed)\n\n"
                
                for category in focus_categories:
                    emails_in_category = categorized_emails.get(category, [])
                    count_in_category = len(emails_in_category)
                    
                    if count_in_category > 0:
                        category_icon = {
                            "work": "💼",
                            "personal": "👤", 
                            "promotions": "🛍️",
                            "social": "👥",
                            "important": "⭐",
                            "newsletters": "📰",
                            "spam": "🚫"
                        }.get(category, "📧")
                        
                        formatted_categories += f"{category_icon} **{category.title()}** ({count_in_category} emails)\n"
                        
                        # Show first few emails in each category
                        for i, email in enumerate(emails_in_category[:3], 1):
                            sender = email.get('from', 'Unknown')
                            if '<' in sender and '>' in sender:
                                sender_name = sender.split('<')[0].strip().strip('"')
                            else:
                                sender_name = sender
                            
                            subject = email.get('subject', 'No Subject')
                            if len(subject) > 40:
                                subject = subject[:37] + '...'
                                
                            formatted_categories += f"   {i}. {sender_name}: {subject}\n"
                        
                        if count_in_category > 3:
                            formatted_categories += f"   ... and {count_in_category - 3} more emails\n"
                        
                        formatted_categories += "\n"
                
                return {
                    "success": True,
                    "data": {
                        "count": len(emails_data),
                        "categories": formatted_categories,
                        "categorized_emails": categorized_emails,
                        "category_counts": {cat: len(emails) for cat, emails in categorized_emails.items()}
                    },
                    "message": f"Successfully categorized {len(emails_data)} emails"
                }
            
            return {"success": False, "data": {}, "message": "Enhanced Gmail automation not implemented"}
            
        except Exception as e:
            logger.error(f"Enhanced Gmail automation error: {e}")
            return {"success": False, "data": {}, "message": str(e)}

    async def _handle_linkedin_automation(self, intent: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn-related automation"""
        try:
            if intent == "check_linkedin_notifications":
                # For demo purposes, simulate notification check
                # In production, this would use playwright_service.scrape_linkedin_insights
                mock_notifications = [
                    {"type": "connection", "name": "John Doe", "message": "wants to connect"},
                    {"type": "message", "name": "Sarah Smith", "message": "sent you a message"},
                    {"type": "post_like", "name": "Mike Johnson", "message": "liked your post"}
                ]
                
                return {
                    "success": True,
                    "data": {
                        "count": len(mock_notifications),
                        "notifications": mock_notifications
                    },
                    "message": "Notifications retrieved successfully"
                }
            
            elif intent == "linkedin_job_alerts":
                # For demo purposes, simulate job alerts
                mock_jobs = [
                    {
                        "title": "Senior Software Engineer", 
                        "company": "Tech Corp", 
                        "location": "Remote",
                        "posted": "2 days ago"
                    },
                    {
                        "title": "Full Stack Developer", 
                        "company": "StartupX", 
                        "location": "New York",
                        "posted": "1 day ago"
                    }
                ]
                
                return {
                    "success": True,
                    "data": {
                        "count": len(mock_jobs),
                        "jobs": mock_jobs
                    },
                    "message": "Job alerts retrieved successfully"
                }
            
            return {"success": False, "data": {}, "message": "LinkedIn automation not implemented"}
            
        except Exception as e:
            return {"success": False, "data": {}, "message": str(e)}
    

    async def _handle_data_extraction(self, intent: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data extraction automation"""
        try:
            if intent == "scrape_product_listings":
                category = intent_data.get("category", "electronics")
                platform = intent_data.get("platform", "amazon")
                
                # For demo purposes, simulate product listings
                mock_listings = [
                    {
                        "name": "Gaming Laptop X1",
                        "price": "$1,299.99",
                        "rating": "4.5/5",
                        "reviews": "1,234"
                    },
                    {
                        "name": "Professional Laptop Pro",
                        "price": "$899.99", 
                        "rating": "4.3/5",
                        "reviews": "856"
                    },
                    {
                        "name": "Budget Laptop Lite",
                        "price": "$499.99",
                        "rating": "4.1/5", 
                        "reviews": "423"
                    }
                ]
                
                return {
                    "success": True,
                    "data": {
                        "count": len(mock_listings),
                        "listings": mock_listings,
                        "category": category,
                        "platform": platform
                    },
                    "message": "Product listings retrieved successfully"
                }
            
            elif intent == "monitor_competitors":
                company = intent_data.get("company", "Unknown Company")
                data_type = intent_data.get("data_type", "pricing")
                
                # For demo purposes, simulate competitor analysis
                mock_insights = {
                    "pricing": "Competitor reduced prices by 15% this week",
                    "products": "2 new products launched in Q1",
                    "marketing": "Increased social media activity by 40%"
                }
                
                insights = mock_insights.get(data_type, "No insights available")
                
                return {
                    "success": True,
                    "data": {
                        "company": company,
                        "insights": insights,
                        "data_type": data_type,
                        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    "message": "Competitor analysis completed"
                }
            
            return {"success": False, "data": {}, "message": "Data extraction not implemented"}
            
        except Exception as e:
            return {"success": False, "data": {}, "message": str(e)}
    
    async def _handle_web_scraping(self, intent: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle web scraping automation"""
        try:
            if intent == "check_website_updates":
                website = intent_data.get("website", "Unknown Website")
                section = intent_data.get("section", "homepage")
                
                # For demo purposes, simulate website update check
                mock_changes = [
                    "New blog post published: 'AI Trends 2025'",
                    "Product pricing updated in shop section",
                    "2 new team member profiles added"
                ]
                
                return {
                    "success": True,
                    "data": {
                        "website": website,
                        "changes": "\n".join([f"• {change}" for change in mock_changes]),
                        "section": section,
                        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    "message": "Website updates retrieved successfully"
                }
            
            elif intent == "scrape_news_articles":
                topic = intent_data.get("topic", "technology")
                source = intent_data.get("source", "tech news")
                
                # For demo purposes, simulate news scraping
                mock_articles = [
                    {
                        "title": "AI Revolution in Healthcare: New Breakthrough",
                        "source": "Tech Times",
                        "published": "2 hours ago"
                    },
                    {
                        "title": "Quantum Computing Achieves Major Milestone", 
                        "source": "Science Daily",
                        "published": "4 hours ago"
                    },
                    {
                        "title": "Green Technology Investments Surge in 2025",
                        "source": "Clean Energy News",
                        "published": "6 hours ago"
                    }
                ]
                
                return {
                    "success": True,
                    "data": {
                        "count": len(mock_articles),
                        "articles": mock_articles,
                        "topic": topic,
                        "source": source
                    },
                    "message": "News articles retrieved successfully"
                }
            
            return {"success": False, "data": {}, "message": "Web scraping not implemented"}
            
        except Exception as e:
            return {"success": False, "data": {}, "message": str(e)}
    
    def _format_success_result(self, intent: str, data: Dict[str, Any], template_info: Dict[str, str]) -> str:
        """Format successful automation result using template"""
        try:
            if intent == "web_search":
                # Google Search service already provides formatted results
                return data.get("search_results", "No search results found")
            
            elif intent == "check_linkedin_notifications":
                notifications_text = "\n".join([
                    f"• **{notif['name']}** {notif['message']}" 
                    for notif in data.get("notifications", [])
                ])
                return template_info["success_template"].format(
                    count=data.get("count", 0),
                    notifications=notifications_text
                )
            
            elif intent in ["check_gmail_inbox", "check_gmail_unread", "email_inbox_check"]:
                emails = data.get("emails", [])
                if not emails:
                    if intent == "check_gmail_inbox":
                        return "📥 Your Gmail inbox is empty."
                    elif intent in ["check_gmail_unread", "email_inbox_check"]:
                        return "✅ No unread emails! Your inbox is all caught up."
                else:
                    # Beautiful formatted email display as requested
                    email_blocks = []
                    for i, email in enumerate(emails, 1):
                        # Parse sender name from "Name <email>" format
                        sender = email.get('sender', 'Unknown')
                        if '<' in sender and '>' in sender:
                            sender_name = sender.split('<')[0].strip().strip('"')
                        else:
                            sender_name = sender
                        
                        # Format date nicely
                        date_str = email.get('date', 'Unknown Date')
                        try:
                            # Try to parse and format date nicely
                            from datetime import datetime
                            import re
                            
                            # Extract meaningful date parts if possible
                            if 'GMT' in date_str or 'EST' in date_str or 'PST' in date_str:
                                # Try to extract readable date
                                date_match = re.search(r'(\w{3}),?\s+(\d{1,2})\s+(\w{3})\s+(\d{4})\s+(\d{1,2}):(\d{2})', date_str)
                                if date_match:
                                    day, date_num, month, year, hour, minute = date_match.groups()
                                    date_str = f"{month} {date_num}, {year}, {hour}:{minute}"
                        except:
                            pass  # Keep original date if parsing fails
                        
                        subject = email.get('subject', 'No Subject')
                        snippet = email.get('snippet', '')
                        
                        # Truncate snippet if too long
                        if len(snippet) > 60:
                            snippet = snippet[:57] + '...'
                        
                        email_block = f"""**{i}.** 🧑 **From:** {sender_name}
   📨 **Subject:** {subject}
   🕒 **Received:** {date_str}
   ✏️ **Snippet:** "{snippet}\""""
                        
                        email_blocks.append(email_block)
                    
                    count = len(emails)
                    header = f"📥 **You have {count} {'unread email' if count == 1 else 'unread emails'}:**\n\n"
                    
                    return header + "\n\n".join(email_blocks)
            
            # Enhanced Gmail intent formatting
            elif intent == "summarize_gmail_emails":
                return data.get("summary", "No summary available")
            
            elif intent == "search_gmail_emails":
                return data.get("search_results", "No search results available")
            
            elif intent == "categorize_gmail_emails":
                return data.get("categories", "No categorization available")
                    
            elif intent in ["check_gmail_inbox", "check_gmail_unread"]:
                emails_text = "\n".join([
                    f"• **{email.get('sender', 'Unknown')}**: {email.get('subject', 'No Subject')} {('🔴' if email.get('unread', False) else '')}"
                    for email in data.get("emails", [])
                ])
                if not emails_text:
                    emails_text = "No emails found" if intent == "check_gmail_inbox" else "No unread emails"
                    
                return template_info["success_template"].format(
                    count=data.get("count", 0),
                    emails=emails_text
                )
            

            elif intent == "scrape_product_listings":
                listings_text = "\n".join([
                    f"• **{listing['name']}** - {listing['price']} ⭐ {listing['rating']} ({listing['reviews']} reviews)"
                    for listing in data.get("listings", [])
                ])
                return template_info["success_template"].format(
                    count=data.get("count", 0),
                    listings=listings_text
                )
            
            elif intent == "linkedin_job_alerts":
                jobs_text = "\n".join([
                    f"• **{job['title']}** at {job['company']} ({job['location']}) - {job['posted']}"
                    for job in data.get("jobs", [])
                ])
                return template_info["success_template"].format(
                    count=data.get("count", 0),
                    jobs=jobs_text
                )
            
            elif intent == "check_website_updates":
                return template_info["success_template"].format(**data)
            
            elif intent == "monitor_competitors":
                return template_info["success_template"].format(**data)
            
            elif intent == "scrape_news_articles":
                articles_text = "\n".join([
                    f"• **{article['title']}** ({article['source']}) - {article['published']}"
                    for article in data.get("articles", [])
                ])
                return template_info["success_template"].format(
                    count=data.get("count", 0),
                    articles=articles_text
                )
            
            return f"✅ Automation completed successfully\n{data}"
            
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return f"✅ Automation completed successfully\n{data}"

    async def _basic_email_summarization(self, emails_data: List[Dict], count: int, time_filter: str, include_unread_only: bool) -> Dict[str, Any]:
        """Fallback basic email summarization when SuperAGI is unavailable"""
        try:
            summary_lines = []
            summary_lines.append(f"📧 **Basic Email Summary** ({len(emails_data)} emails)")
            summary_lines.append("")
            
            # Group emails by sender
            sender_groups = {}
            for email in emails_data:
                sender = email.get('from', 'Unknown')
                if '<' in sender and '>' in sender:
                    sender_name = sender.split('<')[0].strip().strip('"')
                else:
                    sender_name = sender
                
                if sender_name not in sender_groups:
                    sender_groups[sender_name] = []
                sender_groups[sender_name].append(email)
            
            # Show summary by sender
            for sender, sender_emails in list(sender_groups.items())[:5]:  # Top 5 senders
                email_count = len(sender_emails)
                if email_count == 1:
                    subject = sender_emails[0].get('subject', 'No Subject')
                    summary_lines.append(f"• **{sender}**: {subject}")
                else:
                    subjects = [e.get('subject', 'No Subject') for e in sender_emails[:2]]
                    summary_lines.append(f"• **{sender}** ({email_count} emails): {', '.join(subjects)}")
                    if email_count > 2:
                        summary_lines.append(f"  ... and {email_count - 2} more")
            
            # Add basic insights
            summary_lines.append("")
            summary_lines.append("💡 **Quick Insights:**")
            summary_lines.append(f"• Total emails: {len(emails_data)}")
            summary_lines.append(f"• Unique senders: {len(sender_groups)}")
            summary_lines.append(f"• Time period: {time_filter}")
            
            summary_text = "\n".join(summary_lines)
            
            return {
                "success": True,
                "data": {
                    "count": len(emails_data),
                    "summary": summary_text,
                    "key_insights": [f"Received emails from {len(sender_groups)} different senders"],
                    "suggested_actions": ["Review emails from frequent senders", "Check for urgent messages"],
                    "time_filter": time_filter,
                    "include_unread_only": include_unread_only
                },
                "message": f"Basic summarization completed for {len(emails_data)} emails"
            }
            
        except Exception as e:
            logger.error(f"Basic email summarization error: {e}")
            return {
                "success": False,
                "data": {"count": 0, "summary": ""},
                "message": f"Summarization failed: {str(e)}"
            }

    async def _categorize_emails_with_ai(self, emails_data: List[Dict], categories: List[str]) -> Dict[str, List[Dict]]:
        """AI-powered email categorization using Groq for classification"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain.prompts import ChatPromptTemplate
            import os
            import json
            
            # Initialize Groq LLM for categorization
            llm = ChatOpenAI(
                temperature=0.1,
                openai_api_key=os.getenv("GROQ_API_KEY"),
                model="llama3-8b-8192",
                base_url="https://api.groq.com/openai/v1"
            )
            
            categorized_emails = {category: [] for category in categories}
            
            # Process emails in batches of 5 for efficiency
            batch_size = 5
            for i in range(0, len(emails_data), batch_size):
                batch = emails_data[i:i + batch_size]
                
                # Create categorization prompt
                prompt = ChatPromptTemplate.from_messages([
                    ("system", f"""You are an email categorization expert. Categorize each email into one of these categories: {', '.join(categories)}.

Consider:
- Work emails: professional communications, business matters, work-related updates
- Personal emails: friends, family, personal communications  
- Promotions: marketing emails, offers, deals, sales
- Social: social media notifications, community updates
- Important: urgent matters, time-sensitive information
- Newsletters: news, subscriptions, updates
- Spam: unwanted or suspicious emails

Return JSON with email index (0-based) as key and category as value.
Example: {{"0": "work", "1": "personal", "2": "promotions"}}"""),
                    ("user", "Categorize these emails:\n{emails}")
                ])
                
                # Format batch emails for analysis
                batch_text = ""
                for j, email in enumerate(batch):
                    sender = email.get('from', 'Unknown')
                    subject = email.get('subject', 'No Subject')
                    snippet = email.get('snippet', '')[:100]  # First 100 chars
                    
                    batch_text += f"Email {j}:\n"
                    batch_text += f"From: {sender}\n"
                    batch_text += f"Subject: {subject}\n"
                    batch_text += f"Content preview: {snippet}\n\n"
                
                try:
                    # Get AI categorization
                    chain = prompt | llm
                    response = chain.invoke({"emails": batch_text})
                    
                    # Parse categorization results
                    try:
                        categorization = json.loads(response.content)
                        for email_idx, category in categorization.items():
                            batch_idx = int(email_idx)
                            if 0 <= batch_idx < len(batch) and category in categories:
                                categorized_emails[category].append(batch[batch_idx])
                            else:
                                # Default to 'personal' if category not recognized
                                categorized_emails.get('personal', categorized_emails.get(categories[0], [])).append(batch[batch_idx])
                    except (json.JSONDecodeError, ValueError):
                        # Fallback: simple keyword-based categorization
                        for email in batch:
                            category = self._simple_categorize_email(email, categories)
                            categorized_emails[category].append(email)
                            
                except Exception as batch_error:
                    logger.error(f"Batch categorization error: {batch_error}")
                    # Fallback for this batch
                    for email in batch:
                        category = self._simple_categorize_email(email, categories)
                        categorized_emails[category].append(email)
            
            return categorized_emails
            
        except Exception as e:
            logger.error(f"AI categorization error: {e}")
            # Ultimate fallback: simple categorization
            categorized_emails = {category: [] for category in categories}
            for email in emails_data:
                category = self._simple_categorize_email(email, categories)
                categorized_emails[category].append(email)
            return categorized_emails

    def _simple_categorize_email(self, email: Dict[str, Any], categories: List[str]) -> str:
        """Simple keyword-based email categorization as fallback"""
        sender = email.get('from', '').lower()
        subject = email.get('subject', '').lower()
        snippet = email.get('snippet', '').lower()
        
        content = f"{sender} {subject} {snippet}"
        
        # Work-related keywords
        if any(keyword in content for keyword in ['meeting', 'project', 'work', 'office', 'team', 'business', 'client', 'deadline', 'report']):
            return 'work' if 'work' in categories else categories[0]
        
        # Promotion keywords
        if any(keyword in content for keyword in ['sale', 'offer', 'discount', 'deal', 'promo', 'buy', 'shop', 'limited time', 'special']):
            return 'promotions' if 'promotions' in categories else categories[0]
        
        # Social keywords  
        if any(keyword in content for keyword in ['facebook', 'twitter', 'linkedin', 'instagram', 'social', 'notification', 'friend', 'like', 'comment']):
            return 'social' if 'social' in categories else categories[0]
        
        # Newsletter keywords
        if any(keyword in content for keyword in ['newsletter', 'unsubscribe', 'weekly', 'monthly', 'digest', 'news', 'update']):
            return 'newsletters' if 'newsletters' in categories else categories[0]
        
        # Important keywords
        if any(keyword in content for keyword in ['urgent', 'important', 'asap', 'emergency', 'critical', 'immediate']):
            return 'important' if 'important' in categories else categories[0]
        
        # Default to personal
        return 'personal' if 'personal' in categories else categories[0]

    async def _handle_weather_automation(self, intent: str, intent_data: Dict[str, Any], username: str = None) -> Dict[str, Any]:
        """Handle weather automation using Tomorrow.io API with friendly responses"""
        try:
            location = intent_data.get("location", "")
            
            if not location:
                return {
                    "success": False,
                    "data": {},
                    "message": "❌ No location specified for weather request"
                }
            
            logger.info(f"🌦️ Processing weather intent '{intent}' for location: {location}")
            
            if intent == "get_current_weather":
                weather_data = await get_current_weather(location, username)
                return {
                    "success": True,
                    "data": {"weather_data": weather_data, "location": location},
                    "message": weather_data  # Return friendly message directly
                }
            
            elif intent == "get_weather_forecast":
                days = intent_data.get("days", 3)
                # Ensure days is within valid range
                days = max(1, min(days, 7))
                weather_data = await get_weather_forecast(location, days, username)
                return {
                    "success": True,
                    "data": {"weather_data": weather_data, "location": location, "days": days},
                    "message": weather_data  # Return friendly message directly
                }
            
            elif intent == "get_air_quality_index":
                weather_data = await get_air_quality_index(location)
                return {
                    "success": True,
                    "data": {"weather_data": weather_data, "location": location},
                    "message": weather_data  # Return the data directly for consistency
                }
            
            elif intent == "get_weather_alerts":
                weather_data = await get_weather_alerts(location)
                return {
                    "success": True,
                    "data": {"weather_data": weather_data, "location": location},
                    "message": weather_data  # Return the data directly for consistency
                }
            
            elif intent == "get_sun_times":
                weather_data = await get_sun_times(location)
                return {
                    "success": True,
                    "data": {"weather_data": weather_data, "location": location},
                    "message": weather_data  # Return the data directly for consistency
                }
            
            else:
                return {
                    "success": False,
                    "data": {},
                    "message": f"❌ Unknown weather intent: {intent}"
                }
            
        except Exception as e:
            logger.error(f"Weather automation error for {intent}: {e}")
            return {
                "success": False,
                "data": {},
                "message": f"❌ Weather service error: {str(e)}"
            }

# Global instance
direct_automation_handler = DirectAutomationHandler()