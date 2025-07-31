# SuperAGI Integration Service
# Connects Elva AI with SuperAGI autonomous agents

import os
import json
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SuperAGIClient:
    """Client for interacting with SuperAGI API"""
    
    def __init__(self):
        self.base_url = os.getenv("SUPERAGI_BASE_URL", "http://localhost:8001")
        self.api_key = os.getenv("SUPERAGI_API_KEY", "superagi-api-key")
        self.mcp_url = os.getenv("MCP_SERVICE_URL", "http://localhost:8002")
        self.mcp_token = os.getenv("MCP_API_TOKEN", "mcp-secret-token-elva-ai")
        
        # Agent configurations
        self.agents = {
            "email_agent": {
                "id": "email-summarizer-agent",
                "name": "Email Agent",
                "description": "Summarizes emails and drafts responses",
                "tools": ["gmail_reader", "email_composer", "mcp_reader"]
            },
            "linkedin_agent": {
                "id": "linkedin-post-agent", 
                "name": "LinkedIn Agent",
                "description": "Generates LinkedIn post ideas and instructions",
                "tools": ["content_generator", "mcp_reader", "post_optimizer"]
            },
            "research_agent": {
                "id": "web-research-agent",
                "name": "Web Research Agent", 
                "description": "Performs web research and finds trending topics",
                "tools": ["web_scraper", "google_search", "content_analyzer", "mcp_writer"]
            }
        }
    
    async def run_task(self, session_id: str, goal: str, agent_type: str = "auto") -> Dict[str, Any]:
        """
        Main method to run a task with SuperAGI agents
        
        Args:
            session_id: Session identifier for context
            goal: Task description/goal
            agent_type: Which agent to use (email_agent, linkedin_agent, research_agent, auto)
        
        Returns:
            Task result from SuperAGI
        """
        try:
            logger.info(f"🤖 Running SuperAGI task: {goal} (agent: {agent_type})")
            
            # Step 1: Read context from MCP
            context = await self._read_mcp_context(session_id)
            
            # Step 2: Determine agent if auto
            if agent_type == "auto":
                agent_type = self._determine_agent(goal, context)
            
            # Step 3: Execute task with appropriate agent
            result = await self._execute_agent_task(agent_type, goal, context, session_id)
            
            # Step 4: Write results back to MCP
            await self._write_mcp_result(session_id, result, agent_type)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ SuperAGI task execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Task execution failed",
                "session_id": session_id
            }
    
    async def _read_mcp_context(self, session_id: str) -> Dict[str, Any]:
        """Read context from MCP service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mcp_url}/context/read/{session_id}",
                    headers={"Authorization": f"Bearer {self.mcp_token}"}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"No context found for session: {session_id}")
                    return {"context": {}, "appends": []}
                else:
                    response.raise_for_status()
                    
        except Exception as e:
            logger.error(f"❌ Failed to read MCP context: {e}")
            return {"context": {}, "appends": []}
    
    async def _write_mcp_result(self, session_id: str, result: Dict[str, Any], agent_type: str):
        """Write agent results back to MCP"""
        try:
            append_data = {
                "session_id": session_id,
                "output": result,
                "source": f"superagi_{agent_type}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_url}/context/append",
                    json=append_data,
                    headers={"Authorization": f"Bearer {self.mcp_token}"}
                )
                response.raise_for_status()
                
            logger.info(f"📝 MCP result written for session: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to write MCP result: {e}")
    
    def _determine_agent(self, goal: str, context: Dict[str, Any]) -> str:
        """Determine which agent to use based on goal and context"""
        goal_lower = goal.lower()
        
        # Email-related keywords
        if any(keyword in goal_lower for keyword in ['email', 'inbox', 'mail', 'message', 'compose', 'draft']):
            return "email_agent"
        
        # LinkedIn-related keywords  
        if any(keyword in goal_lower for keyword in ['linkedin', 'post', 'social', 'share', 'professional']):
            return "linkedin_agent"
        
        # Research-related keywords
        if any(keyword in goal_lower for keyword in ['research', 'find', 'search', 'trending', 'news', 'topic']):
            return "research_agent"
        
        # Default to email agent if context contains email data
        if context.get("context", {}).get("data", {}).get("emails"):
            return "email_agent"
        
        # Default to research agent
        return "research_agent"
    
    async def _execute_agent_task(self, agent_type: str, goal: str, context: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute task with specific agent"""
        
        if agent_type == "email_agent":
            return await self._execute_email_agent(goal, context, session_id)
        elif agent_type == "linkedin_agent":
            return await self._execute_linkedin_agent(goal, context, session_id)
        elif agent_type == "research_agent":
            return await self._execute_research_agent(goal, context, session_id)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    async def _execute_email_agent(self, goal: str, context: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute task with Email Agent"""
        try:
            logger.info(f"📧 Executing Email Agent task: {goal}")
            
            # Extract email data from context
            context_data = context.get("context", {}).get("data", {})
            emails = context_data.get("emails", [])
            
            # Use Groq for email summarization (free API)
            summary_result = await self._summarize_emails_with_groq(emails, goal)
            
            return {
                "success": True,
                "agent": "email_agent",
                "task": goal,
                "email_summary": summary_result.get("summary", ""),
                "email_count": len(emails),
                "key_insights": summary_result.get("insights", []),
                "suggested_actions": summary_result.get("actions", []),
                "session_id": session_id,
                "execution_time": summary_result.get("execution_time", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Email Agent execution error: {e}")
            return {
                "success": False,
                "agent": "email_agent", 
                "error": str(e),
                "session_id": session_id
            }
    
    async def _execute_linkedin_agent(self, goal: str, context: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute task with LinkedIn Agent"""
        try:
            logger.info(f"💼 Executing LinkedIn Agent task: {goal}")
            
            # Extract relevant data from context
            context_data = context.get("context", {}).get("data", {})
            intent_data = context_data.get("intent_data", {})
            
            # Use Groq for LinkedIn content generation (free API)
            content_result = await self._generate_linkedin_content_with_groq(goal, intent_data)
            
            return {
                "success": True,
                "agent": "linkedin_agent",
                "task": goal,
                "post_description": content_result.get("post_description", ""),
                "ai_instructions": content_result.get("ai_instructions", ""),
                "suggested_hashtags": content_result.get("hashtags", []),
                "content_themes": content_result.get("themes", []),
                "session_id": session_id,
                "execution_time": content_result.get("execution_time", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ LinkedIn Agent execution error: {e}")
            return {
                "success": False,
                "agent": "linkedin_agent",
                "error": str(e),
                "session_id": session_id
            }
    
    async def _execute_research_agent(self, goal: str, context: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute task with Research Agent"""
        try:
            logger.info(f"🔍 Executing Research Agent task: {goal}")
            
            # Use free web scraping and search
            research_result = await self._perform_web_research(goal)
            
            return {
                "success": True,
                "agent": "research_agent",
                "task": goal,
                "research_summary": research_result.get("summary", ""),
                "trending_topics": research_result.get("topics", []),
                "key_findings": research_result.get("findings", []),
                "sources": research_result.get("sources", []),
                "session_id": session_id,
                "execution_time": research_result.get("execution_time", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Research Agent execution error: {e}")
            return {
                "success": False,
                "agent": "research_agent",
                "error": str(e),
                "session_id": session_id
            }
    
    async def _summarize_emails_with_groq(self, emails: List[Dict], goal: str) -> Dict[str, Any]:
        """Summarize emails using Groq free API"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain.prompts import ChatPromptTemplate
            import time
            
            start_time = time.time()
            
            # Initialize Groq LLM
            llm = ChatOpenAI(
                temperature=0.1,
                openai_api_key=os.getenv("GROQ_API_KEY"),
                model="llama3-8b-8192",
                base_url="https://api.groq.com/openai/v1"
            )
            
            # Create email summary prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an AI email assistant. Analyze the provided emails and create a comprehensive summary.

Focus on:
1. Key themes and topics
2. Important actions needed
3. Priority emails
4. Key insights and patterns

Return your response in this JSON format:
{
    "summary": "Overall summary of emails",
    "insights": ["insight1", "insight2", "insight3"],
    "actions": ["action1", "action2", "action3"]
}"""),
                ("user", "Goal: {goal}\n\nEmails to analyze:\n{emails}")
            ])
            
            # Format emails for analysis
            email_text = ""
            for i, email in enumerate(emails[:10], 1):  # Limit to 10 emails
                email_text += f"Email {i}:\n"
                email_text += f"From: {email.get('sender', 'Unknown')}\n"
                email_text += f"Subject: {email.get('subject', 'No subject')}\n"
                email_text += f"Content: {email.get('snippet', email.get('body', ''))[:200]}...\n\n"
            
            # Generate summary
            chain = prompt | llm
            response = chain.invoke({"goal": goal, "emails": email_text})
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                result = {
                    "summary": response.content,
                    "insights": ["Email summary generated"],
                    "actions": ["Review email details"]
                }
            
            result["execution_time"] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"❌ Email summarization error: {e}")
            return {
                "summary": f"Email analysis failed: {str(e)}",
                "insights": [],
                "actions": [],
                "execution_time": 0
            }
    
    async def _generate_linkedin_content_with_groq(self, goal: str, intent_data: Dict) -> Dict[str, Any]:
        """Generate LinkedIn content using Groq free API"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain.prompts import ChatPromptTemplate
            import time
            
            start_time = time.time()
            
            # Initialize Groq LLM
            llm = ChatOpenAI(
                temperature=0.3,  # Slightly more creative
                openai_api_key=os.getenv("GROQ_API_KEY"),
                model="llama3-8b-8192",
                base_url="https://api.groq.com/openai/v1"
            )
            
            # Create LinkedIn content prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a LinkedIn content strategist. Create compelling post descriptions and AI instructions.

Return your response in this JSON format:
{
    "post_description": "First-person description of the achievement/project as if YOU accomplished it",
    "ai_instructions": "Direct commands to an AI for generating the LinkedIn post",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "themes": ["theme1", "theme2", "theme3"]
}"""),
                ("user", "Goal: {goal}\n\nContext data: {context}")
            ])
            
            # Generate content
            chain = prompt | llm
            response = chain.invoke({
                "goal": goal, 
                "context": json.dumps(intent_data, indent=2)
            })
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                result = {
                    "post_description": f"Professional achievement related to: {goal}",
                    "ai_instructions": f"Create a LinkedIn post about: {goal}. Include relevant hashtags and professional tone.",
                    "hashtags": ["#Professional", "#Achievement", "#Growth"],
                    "themes": ["career", "achievement", "learning"]
                }
            
            result["execution_time"] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"❌ LinkedIn content generation error: {e}")
            return {
                "post_description": f"Content generation failed: {str(e)}",
                "ai_instructions": "Generate a professional LinkedIn post",
                "hashtags": [],
                "themes": [],
                "execution_time": 0
            }
    
    async def _perform_web_research(self, goal: str) -> Dict[str, Any]:
        """Perform web research using free APIs and scraping"""
        try:
            import time
            from langchain_openai import ChatOpenAI
            
            start_time = time.time()
            
            # For now, use Groq to generate research insights
            # In production, this would use web scraping and search APIs
            llm = ChatOpenAI(
                temperature=0.2,
                openai_api_key=os.getenv("GROQ_API_KEY"),
                model="llama3-8b-8192",
                base_url="https://api.groq.com/openai/v1"
            )
            
            research_prompt = f"""Research goal: {goal}
            
            Based on current trends and common knowledge, provide:
            1. Summary of key information
            2. 3-5 trending topics related to this area
            3. Key findings and insights
            4. Potential sources to explore
            
            Format as JSON:
            {{
                "summary": "Research summary",
                "topics": ["topic1", "topic2", "topic3"],
                "findings": ["finding1", "finding2", "finding3"],
                "sources": ["source1", "source2", "source3"]
            }}
            """
            
            response = await llm.ainvoke(research_prompt)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = {
                    "summary": response.content,
                    "topics": [goal],
                    "findings": ["Research insights generated"],
                    "sources": ["AI knowledge base"]
                }
            
            result["execution_time"] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"❌ Web research error: {e}")
            return {
                "summary": f"Research failed: {str(e)}",
                "topics": [],
                "findings": [],
                "sources": [],
                "execution_time": 0
            }

# Global SuperAGI client instance
superagi_client = SuperAGIClient()