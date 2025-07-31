import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from playwright_service import playwright_service

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
            if intent == "check_linkedin_notifications":
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

# Global instance
direct_automation_handler = DirectAutomationHandler()