import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

// Generate stable UUID-like ID
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};
import { useToast } from './context/ToastContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Stable ID generator to prevent flickering
let messageCounter = 0;

function ChatBox({ sessionId, gmailAuthStatus, setGmailAuthStatus, messages, setMessages }) {
  const { showGmailSuccess, showGmailError } = useToast();
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editedData, setEditedData] = useState(null);
  const [lastIntentData, setLastIntentData] = useState(null);
  const [currentMessageId, setCurrentMessageId] = useState(null);
  const [automationStatus, setAutomationStatus] = useState(null);
  const [isDirectAutomation, setIsDirectAutomation] = useState(false);
  
      const [userEmail, setUserEmail] = useState(null);
    
  const messagesEndRef = useRef(null);

  // Stable ID generator to prevent flickering - using UUID instead of Date.now()
  const generateStableId = useCallback((prefix = 'msg') => {
    messageCounter += 1;
    return `${prefix}_${sessionId}_${messageCounter}_${generateUUID()}`;
  }, [sessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Check Gmail authentication status
  useEffect(() => {
    checkGmailAuthStatus();
  }, [sessionId]);

  // Handle Gmail OAuth redirect response
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const auth = urlParams.get('auth');
    const service = urlParams.get('service');
    const message = urlParams.get('message');
    const details = urlParams.get('details');
    const returnedSessionId = urlParams.get('session_id');
    
    console.log('🔍 OAuth Redirect Params:', { auth, service, message, details, returnedSessionId, currentSessionId: sessionId });
    
    if (auth === 'success' && service === 'gmail') {
      console.log('✅ Processing Gmail auth success');
      handleGmailAuthSuccess();
      window.history.replaceState({}, document.title, '/');
    } else if (auth === 'error') {
      console.error('❌ Processing Gmail auth error:', message, details);
      handleGmailAuthError(message, details);
      window.history.replaceState({}, document.title, '/');
    }
  }, []);

  const checkGmailAuthStatus = async () => {
    try {
      console.log('🔍 Checking Gmail auth status for session:', sessionId);
      const response = await axios.get(`${API}/gmail/status?session_id=${sessionId}`);
      const data = response.data;
      
      console.log('📊 Gmail Auth Status Response:', data);
      
      setGmailAuthStatus({ 
        authenticated: data.authenticated || false,
        loading: false,
        credentialsConfigured: data.credentials_configured || false,
        error: data.error || null,
        debugInfo: {
          success: data.success,
          requires_auth: data.requires_auth,
          scopes: data.scopes,
          service: data.service,
          session_id: data.session_id
        }
      });
      
      // Add debug information to chat if there are issues
      if (!data.success || !data.credentials_configured || data.error) {
        console.log('🔧 Gmail Auth Issues Detected:', data);
        
        const debugMessage = {
          id: generateStableId('gmail_debug'),
          response: `🔧 **Gmail Connection Debug**\n\n` +
            `📋 **Status**: ${data.success ? 'Service Running' : 'Service Error'}\n` +
            `🔑 **Credentials**: ${data.credentials_configured ? 'Configured ✅' : 'Missing ❌'}\n` +
            `🔐 **Authentication**: ${data.authenticated ? 'Connected ✅' : 'Not Connected ❌'}\n` +
            `🆔 **Session ID**: ${sessionId}\n` +
            (data.error ? `❌ **Error**: ${data.error}\n` : '') +
            `\n` +
            (!data.credentials_configured ? 
              '⚠️ **Issue**: Gmail credentials.json file is missing from backend. This is required for OAuth2 authentication to work properly.' : 
              !data.authenticated ? 
                '💡 Click "Connect Gmail" above to authenticate with your Google account.' : 
                '✅ Everything looks good!'),
          isUser: false,
          isSystem: true,
          timestamp: new Date()
        };
        
        setTimeout(() => {
          setMessages(prev => {
            const hasDebugMessage = prev.some(msg => msg.id && msg.id.startsWith('gmail_debug_'));
            if (!hasDebugMessage) {
              return [...prev, debugMessage];
            }
            return prev;
          });
        }, 1000);
      }
      
    } catch (error) {
      console.error('❌ Gmail auth status check failed:', error);
      setGmailAuthStatus({ 
        authenticated: false, 
        loading: false,
        credentialsConfigured: false,
        error: error.message,
        debugInfo: { error: error.response?.data || error.message }
      });
    }
  };

  const handleGmailAuthSuccess = async () => {
    try {
      await checkGmailAuthStatus();
      
      // Store authentication success in localStorage
      localStorage.setItem('gmail-auth-status', 'true');
      
      // 🔔 Show toast notification instead of chat message
      showGmailSuccess();
      
      console.log('Gmail authentication successful - status updated!');
    } catch (error) {
      console.error('Error handling Gmail auth success:', error);
      showGmailError('Error completing Gmail authentication setup');
    }
  };

  const handleGmailAuthError = (errorMessage, details) => {
    try {
      checkGmailAuthStatus();
      
      let userMessage = 'Gmail authentication failed. Please try again.';
      
      switch(errorMessage) {
        case 'access_denied':
          userMessage = 'Gmail authentication was cancelled';
          break;
        case 'no_code':
          userMessage = 'Gmail authentication failed - no authorization received';
          break;
        case 'auth_failed':
          userMessage = 'Gmail authentication failed during token exchange';
          break;
        case 'server_error':
          userMessage = 'Gmail authentication failed due to a server error';
          break;
        default:
          userMessage = details || `Gmail authentication error: ${errorMessage}`;
      }
      
      console.error('🚨 Gmail Auth Error Details:', { errorMessage, details });
      
      // 🔔 Show toast notification instead of chat message
      showGmailError(userMessage);
      
      console.error('Gmail authentication error processed');
    } catch (error) {
      console.error('Error handling Gmail auth error:', error);
      showGmailError('Gmail authentication failed');
    }
  };

  const getAutomationStatusMessage = (message) => {
    const directAutomationPatterns = {
      'check.*linkedin.*notification': '🔔 Checking LinkedIn notifications...',
      'scrape.*product|product.*listing|find.*product': '🛒 Scraping product listings...',
      'job.*alert|linkedin.*job|check.*job': '💼 Checking LinkedIn job alerts...',
      'website.*update|check.*website': '🔍 Monitoring website updates...',
      'competitor.*monitor|monitor.*competitor': '📊 Analyzing competitor data...',
      'news.*article|scrape.*news|latest.*news': '📰 Gathering latest news...'
    };

    const lowerMessage = message.toLowerCase();
    for (const [pattern, status] of Object.entries(directAutomationPatterns)) {
      if (new RegExp(pattern).test(lowerMessage)) {
        return status;
      }
    }
    return null;
  };

  const isDirectAutomationMessage = (message) => {
    return getAutomationStatusMessage(message) !== null;
  };

  const renderGmailSuccessMessage = useCallback(() => {
    return (
      <div className="gmail-success-message">
        <div className="gmail-success-title">
          🎉 Gmail Authentication Successful!
        </div>
        
        <div style={{ fontWeight: '600', marginBottom: '12px', color: 'rgba(255, 255, 255, 0.9)' }}>
          Your Gmail account has been securely connected using OAuth2. I can now help you with:
        </div>
        
        <ul className="gmail-features-list">
          <li>📧 Check your Gmail inbox</li>
          <li>✉️ Send emails</li>
          <li>📨 Read specific emails</li>
          <li>🔍 Search your messages</li>
        </ul>
        
        <div className="gmail-example-text">
          Try saying: "Check my Gmail inbox" or "Send an email to [someone]"
        </div>
      </div>
    );
  }, []);

  const renderPostPromptPackage = (message) => {
    const intentData = message.intent_data;
    
    if (!intentData || intentData.intent !== 'generate_post_prompt_package') {
      return null;
    }

    return (
      <div className="post-prompt-package-display">
        <div className="package-block post-description-block">
          <div className="block-header">
            <span className="block-icon">📝</span>
            <h3 className="block-title">Post Description</h3>
          </div>
          <div className="block-content">
            {intentData.post_description || "No description available"}
          </div>
        </div>

        <div className="package-block ai-instructions-block">
          <div className="block-header">
            <span className="block-icon">🤖</span>
            <h3 className="block-title">AI Instructions</h3>
          </div>
          <div className="block-content">
            {intentData.ai_instructions || "No instructions available"}
          </div>
        </div>

        <div className="package-confirmation">
          💬 <strong>Ready to send?</strong> Just say <strong>'send'</strong>, <strong>'yes, go ahead'</strong>, or <strong>'submit'</strong> to send this package to your automation workflow!
        </div>
      </div>
    );
  };

  // 🔒 Admin Email Detection and Toggle Functions
  const checkAdminEmail = useCallback(async () => {
    if (!gmailAuthStatus.authenticated) {
      setShowAdminToggle(false);
      return;
    }

    try {
      // Get user email from Gmail API or user info
      const response = await axios.get(`${API}/gmail/user-info`, {
        timeout: 5000
      });
      
      if (response.data.success && response.data.email) {
        const email = response.data.email.toLowerCase();
        setUserEmail(email);
        
        // Check if email is in admin whitelist
        const isAdmin = ADMIN_EMAILS.includes(email);
        setShowAdminToggle(isAdmin);
        
        console.log('Admin check:', { email, isAdmin, showToggle: isAdmin });
      }
    } catch (error) {
      console.log('Admin email check failed (normal for non-admins):', error.message);
      setShowAdminToggle(false);
    }
  }, [gmailAuthStatus.authenticated, ADMIN_EMAILS]);

  // Check for admin email when Gmail status changes
  useEffect(() => {
    if (gmailAuthStatus.authenticated) {
      checkAdminEmail();
    } else {
      setShowAdminToggle(false);
      setIsAdminMode(false);
      setUserEmail(null);
    }
  }, [gmailAuthStatus.authenticated, checkAdminEmail]);

  const toggleAdminMode = () => {
    const newAdminMode = !isAdminMode;
    setIsAdminMode(newAdminMode);
    
    if (newAdminMode) {
      // Show success toast
      const toastEvent = new CustomEvent('show-toast', {
        detail: {
          type: 'success',
          message: '✅ Admin Mode Enabled'
        } 
      });
      window.dispatchEvent(toastEvent);
      
      console.log('🔐 Admin mode enabled for:', userEmail);
    } else {
      console.log('🔐 Admin mode disabled');
    }
  };

  const renderEmailDisplay = useCallback((response) => {
    // Handle authentication prompts - plain text format
    if (response.includes('🔐 Please connect your Gmail account')) {
      return `🔐 Gmail Connection Required\n\nPlease connect your Gmail account to let Elva AI access your inbox.\nClick the "Connect Gmail" button above to continue.`;
    }

    // Check if this is an email display response - Enhanced Gmail detection
    const isGmailResponse = response.includes('📥') || 
                           response.includes('unread email') || 
                           response.includes('Gmail inbox') || 
                           response.includes('**From:**') ||
                           response.includes('**Subject:**') ||
                           response.includes('**Received:**') ||
                           response.includes('**Snippet:**');
    
    if (!isGmailResponse) {
      return response;
    }

    // Handle "no unread emails" message - plain text format
    if (response.includes('No unread emails') || response.includes('all caught up') || response.includes('inbox is empty')) {
      return '✅ No unread emails! Your inbox is all caught up.';
    }

    // If the response contains the special email format, parse and render it as plain text
    if (response.includes('**From:**') && response.includes('**Subject:**')) {
      const lines = response.split('\n');
      const headerLine = lines[0];
      
      // Extract count from header - improved pattern matching
      const countMatch = headerLine.match(/(\d+)\s+(?:unread\s+)?emails?/i);
      const count = countMatch ? parseInt(countMatch[1]) : 0;
      
      if (count === 0) {
        return '✅ No unread emails! Your inbox is all caught up.';
      }

      // Parse individual email blocks - improved parsing
      const emailBlocks = [];
      let currentBlock = null;
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Match email number pattern like "**1.**" or "**2.**"
        if (line.match(/^\*\*\d+\.\*\*/)) {
          if (currentBlock) {
            emailBlocks.push(currentBlock);
          }
          currentBlock = { lines: [line] };
        } else if (currentBlock && line) {
          currentBlock.lines.push(line);
        } else if (!currentBlock && line.includes('**From:**')) {
          // Handle cases where email starts directly with From field
          currentBlock = { lines: [line] };
        }
      }
      
      if (currentBlock) {
        emailBlocks.push(currentBlock);
      }

      // Format as plain text with horizontal lines
      let plainTextResult = `📥 You have ${count} unread email${count !== 1 ? 's' : ''}\n\n`;
      
      emailBlocks.forEach((block, index) => {
        const lines = block.lines;
        let sender = '', subject = '', date = '', snippet = '';
        
        lines.forEach(line => {
          // Enhanced pattern matching for current format
          if (line.includes('**From:**') || line.includes('🧑 **From:**')) {
            sender = line.replace(/.*\*\*From:\*\*\s*/, '').replace(/^🧑\s*/, '').trim();
          } else if (line.includes('**Subject:**') || line.includes('📨 **Subject:**')) {
            subject = line.replace(/.*\*\*Subject:\*\*\s*/, '').replace(/^📨\s*/, '').trim();
          } else if (line.includes('**Received:**') || line.includes('🕒 **Received:**')) {
            date = line.replace(/.*\*\*Received:\*\*\s*/, '').replace(/^🕒\s*/, '').trim();
          } else if (line.includes('**Snippet:**') || line.includes('✏️ **Snippet:**')) {
            snippet = line.replace(/.*\*\*Snippet:\*\*\s*"?/, '').replace(/^✏️\s*/, '').replace(/"$/, '').trim();
          }
        });
        
        // Add email info as plain text
        plainTextResult += `From: ${sender || 'Unknown Sender'}\n`;
        plainTextResult += `Subject: ${subject || 'No Subject'}\n`;
        plainTextResult += `Received: ${date || 'Unknown Date'}\n`;
        if (snippet) {
          plainTextResult += `Snippet: ${snippet}\n`;
        }
        
        // Add horizontal line after each email (except the last one)
        if (index < emailBlocks.length - 1) {
          plainTextResult += '\n────────────────────────────────────────\n\n';
        }
      });
      
      return plainTextResult;
    }

    return response;
  }, []); // Empty dependency array since function doesn't depend on any props/state

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    // Check if user is trying to approve/reject a pending action
    const approvalKeywords = ['send it', 'approve', 'yes', 'confirm', 'execute', 'do it', 'go ahead'];
    const rejectionKeywords = ['cancel', 'no', 'reject', 'don\'t send', 'abort', 'stop'];
    const message = inputMessage.toLowerCase().trim();
    
    // If there's a pending approval and user uses approval/rejection keywords
    if (pendingApproval && (approvalKeywords.some(keyword => message.includes(keyword)) || 
                           rejectionKeywords.some(keyword => message.includes(keyword)))) {
      
      const isApproval = approvalKeywords.some(keyword => message.includes(keyword));
      
      const userMessage = {
        id: generateStableId('user'),
        message: inputMessage,
        isUser: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, userMessage]);
      setInputMessage('');
      
      await handleApproval(isApproval);
      return;
    }

    // If user says approval keywords but there's no pending approval, provide helpful message
    if (!pendingApproval && approvalKeywords.some(keyword => message.includes(keyword))) {
      const userMessage = {
        id: generateStableId('user'),
        message: inputMessage,
        isUser: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, userMessage]);
      setInputMessage('');
      
      const helpMessage = {
        id: generateStableId('response') + 1,
        response: "🤔 I don't see any pending actions to approve. Try asking me to do something first, like 'Send an email to John about the meeting' or 'Create a reminder for tomorrow'!",
        isUser: false,
        isSystem: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, helpMessage]);
      return;
    }

    // Check if this is a direct automation request
    const statusMessage = getAutomationStatusMessage(inputMessage);
    const isDirect = isDirectAutomationMessage(inputMessage);
    
    if (isDirect) {
      setIsDirectAutomation(true);
      setAutomationStatus(statusMessage);
    } else {
      setIsDirectAutomation(false);
      setAutomationStatus(null);
    }

    const userMessage = {
      id: generateStableId('user'),
      message: inputMessage,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setInputMessage('');

    try {
      const response = await axios.post(`${API}/chat`, {
        message: inputMessage,
        session_id: sessionId,
        user_id: 'default_user'
      });

      const data = response.data;

      // Store parsed intent data for modal use
      if (data.intent_data) {
        setLastIntentData(data.intent_data);
        setCurrentMessageId(data.id);
      }

      const aiMessage = {
        id: data.id,
        message: inputMessage,
        response: data.response,
        intent_data: data.intent_data,
        needs_approval: data.needs_approval,
        isUser: false,
        timestamp: new Date(data.timestamp),
        isDirectAutomation: isDirect
      };

      setMessages(prev => [...prev, aiMessage]);

      // Show approval modal immediately if needed with pre-filled data (but not for direct automation)
      if (data.needs_approval && data.intent_data && !isDirect) {
        setPendingApproval(aiMessage);
        setEditedData(data.intent_data);
        setEditMode(true);
        setShowApprovalModal(true);
        
        const modalHelpMessage = {
          id: generateStableId('response') + 1,
          response: "📋 I've opened the approval modal with pre-filled details. You can review and edit the information above, then click 'Approve' or just type 'Send it' to execute! Type 'Cancel' to abort.",
          isUser: false,
          isSystem: true,
          timestamp: new Date()
        };
        setTimeout(() => {
          setMessages(prev => [...prev, modalHelpMessage]);
        }, 500);
      }

      // Add special handling for Gmail debug commands
      if (inputMessage.toLowerCase().includes('gmail debug') || inputMessage.toLowerCase().includes('test gmail')) {
        const debugTestMessage = {
          id: generateStableId('response') + 1,
          response: `🔧 **Gmail Integration Test**\n\n` +
                   `🔗 **Current Status**: ${gmailAuthStatus.authenticated ? 'Connected ✅' : 'Not Connected ❌'}\n` +
                   `🔑 **Credentials**: ${gmailAuthStatus.credentialsConfigured ? 'Configured ✅' : 'Missing ❌'}\n` +
                   `🆔 **Session ID**: ${sessionId}\n\n` +
                   `**🧪 Test Steps:**\n` +
                   `1. Click the "Connect Gmail" button above\n` +
                   `2. You'll be redirected to Google's OAuth page\n` +
                   `3. Grant permissions to your Google account\n` +
                   `4. You'll be redirected back here\n` +
                   `5. You should see a success message in this chat\n` +
                   `6. The button should change to "Gmail Connected ✅"\n\n` +
                   `**💡 Debug Info**: Click the "Debug Info" button next to the Gmail button for technical details.`,
          isUser: false,
          isSystem: true,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, debugTestMessage]);
      }

      // 🔒 Admin Debug Commands - Only available in admin mode
      if (showAdminToggle && isAdminMode && (inputMessage.toLowerCase().includes('show my context') || inputMessage.toLowerCase().includes('show context for session'))) {
        await handleAdminDebugCommand(inputMessage);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: generateStableId('loading'),
        response: 'Sorry, I encountered an error. Please try again! 🤖',
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setAutomationStatus(null);
      setIsDirectAutomation(false);
    }
  };

  // 🔒 Admin Debug Command Handler
  const handleAdminDebugCommand = async (inputMessage) => {
    try {
      let targetSession = sessionId; // Default to current session
      
      // Parse command to extract session ID if specified
      const sessionMatch = inputMessage.match(/show context for session\s+([^\s]+)/i);
      if (sessionMatch) {
        targetSession = sessionMatch[1];
      }
      
      // Call admin debug endpoint with token
      const response = await axios.post(`${API}/admin/debug/context`, {
        command: inputMessage.toLowerCase().includes('show my context') ? 'show my context' : `show context for session ${targetSession}`,
        session_id: targetSession
      }, {
        headers: {
          'X-Debug-Token': 'elva-admin-debug-2024-secure'
        }
      });
      
      if (response.data.success) {
        const debugMessage = {
          id: generateStableId('admin_debug'),
          response: response.data.formatted_context,
          isUser: false,
          isSystem: true,
          isAdminDebug: true,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, debugMessage]);
      } else {
        const errorMessage = {
          id: generateStableId('admin_debug_error'),
          response: `❌ **Admin Debug Error**\n\n${response.data.error || 'Failed to retrieve context'}`,
          isUser: false,
          isSystem: true,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
      
    } catch (error) {
      console.error('Admin debug command error:', error);
      const errorMessage = {
        id: generateStableId('admin_debug_error'),
        response: `❌ **Admin Debug Error**\n\nFailed to execute debug command: ${error.response?.data?.detail || error.message}`,
        isUser: false,
        isSystem: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  // Helper function to format updated email details nicely
  const formatUpdatedDetails = (data) => {
    if (!data) return 'No updates made.';
    
    const intent = data.intent || 'unknown';
    let formattedMessage = '';
    
    if (intent === 'send_email') {
      const recipientName = data.recipient_name || 'Unknown';
      formattedMessage = `📧 Here's the updated email for ${recipientName}:\n\n`;
      formattedMessage += `Subject: ${data.subject || 'No subject'}\n\n`;
      formattedMessage += `Body: ${data.body || 'No content'}`;
      if (data.recipient_email) {
        formattedMessage += `\n\nTo: ${data.recipient_email}`;
      }
    } else if (intent === 'create_event') {
      formattedMessage = `📅 Here's the updated meeting details:\n\n`;
      formattedMessage += `Event: ${data.event_title || data.title || 'No title'}\n\n`;
      if (data.date) formattedMessage += `Date: ${data.date}\n`;
      if (data.time) formattedMessage += `Time: ${data.time}\n`;
      if (data.location) formattedMessage += `Location: ${data.location}\n`;
      if (data.participants && Array.isArray(data.participants)) {
        formattedMessage += `Participants: ${data.participants.join(', ')}\n`;
      }
      if (data.description) formattedMessage += `\nDescription:\n${data.description}`;
    } else if (intent === 'add_todo') {
      formattedMessage = `✅ Here's the updated todo:\n\n`;
      formattedMessage += `Task: ${data.task || 'No task specified'}\n`;
      if (data.priority) formattedMessage += `Priority: ${data.priority}\n`;
      if (data.due_date) formattedMessage += `Due Date: ${data.due_date}\n`;
      if (data.description) formattedMessage += `\nNotes:\n${data.description}`;
    } else if (intent === 'set_reminder') {
      formattedMessage = `⏰ Here's the updated reminder:\n\n`;
      formattedMessage += `Reminder: ${data.reminder_text || data.text || 'No reminder text'}\n`;
      if (data.date) formattedMessage += `Date: ${data.date}\n`;
      if (data.time) formattedMessage += `Time: ${data.time}\n`;
    } else {
      // Generic formatting for other intents
      formattedMessage = `📋 Here are the updated details:\n\n`;
      Object.entries(data).forEach(([key, value]) => {
        if (key !== 'intent') {
          const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          if (Array.isArray(value)) {
            formattedMessage += `${formattedKey}: ${value.join(', ')}\n`;
          } else {
            formattedMessage += `${formattedKey}: ${value}\n`;
          }
        }
      });
    }
    
    return formattedMessage;
  };

  const handleApproval = async (approved) => {
    if (!pendingApproval) return;

    try {
      let finalData = editedData;
      
      if (editMode && editedData) {
        const editSummary = {
          id: generateStableId('response'),
          response: formatUpdatedDetails(editedData),
          isUser: false,
          isEdit: false, // Changed from true to false so it doesn't use green edit styling
          timestamp: new Date()
        };
        setMessages(prev => [...prev, editSummary]);
      }

      const response = await axios.post(`${API}/approve`, {
        session_id: sessionId,
        message_id: currentMessageId || pendingApproval.id,
        approved: approved,
        edited_data: editMode ? finalData : null
      });

      const statusMessage = {
        id: generateStableId('response'),
        response: approved ? 
          '✅ Perfect! Action executed successfully! Your request has been sent to the automation system.' : 
          '❌ No worries! Action cancelled as requested.',
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, statusMessage]);

      // Note: Automation response display removed as requested by user
      // if (approved && response.data.n8n_response) {
      //   const n8nMessage = {
      //     id: Date.now() + 1,
      //     response: `🔗 Automation Response: ${JSON.stringify(response.data.n8n_response, null, 2)}`,
      //     isUser: false,
      //     isSystem: true,
      //     timestamp: new Date()
      //   };
      //   setMessages(prev => [...prev, n8nMessage]);
      // }

    } catch (error) {
      console.error('Error handling approval:', error);
      const errorMessage = {
        id: generateStableId('response'),
        response: '⚠️ Something went wrong with the approval. Please try again!',
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setShowApprovalModal(false);
      setPendingApproval(null);
      setEditMode(false);
      setEditedData(null);
      setLastIntentData(null);
      setCurrentMessageId(null);
    }
  };

  const renderIntentData = (intentData) => {
    // Hide intent data completely for cleaner chat experience
    return null;
  };

  const renderEditForm = () => {
    if (!editedData) return null;

    const handleFieldChange = (field, value) => {
      setEditedData(prev => ({
        ...prev,
        [field]: value
      }));
    };

    return (
      <div className="space-y-4">
        <h4 className="text-sm font-medium text-blue-300 flex items-center">
          <span className="mr-2">✏️</span>
          Edit Action Details:
        </h4>
        <div className="bg-blue-900/20 p-4 rounded-lg border border-blue-500/30">
          {Object.entries(editedData).map(([key, value]) => {
            if (key === 'intent') return null;
            
            return (
              <div key={key} className="mb-3 last:mb-0">
                <label className="block text-sm text-blue-200 mb-2 capitalize font-medium">
                  {key.replace(/_/g, ' ')}:
                </label>
                {Array.isArray(value) ? (
                  <input
                    type="text"
                    value={value.join(', ')}
                    onChange={(e) => handleFieldChange(key, e.target.value.split(', ').filter(v => v.trim()))}
                    className="w-full px-4 py-3 bg-gray-800 border border-blue-500/30 rounded-lg text-white text-sm focus:border-blue-400/60 focus:ring-2 focus:ring-blue-400/20 transition-all duration-200 placeholder-gray-500"
                    placeholder={`Enter ${key.replace(/_/g, ' ')}...`}
                  />
                ) : (
                  <textarea
                    value={value || ''}
                    onChange={(e) => handleFieldChange(key, e.target.value)}
                    rows={key === 'body' || key === 'post_content' ? 4 : 2}
                    className="w-full px-4 py-3 bg-gray-800 border border-blue-500/30 rounded-lg text-white text-sm resize-none focus:border-blue-400/60 focus:ring-2 focus:ring-blue-400/20 transition-all duration-200 placeholder-gray-500"
                    placeholder={`Enter ${key.replace(/_/g, ' ')}...`}
                  />
                )}
              </div>
            );
          })}
        </div>
        
        <div className="mt-4 p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
          <div className="text-xs text-green-300 mb-2">✅ Current Values Preview:</div>
          <pre className="text-xs text-green-200 whitespace-pre-wrap font-mono">
            {JSON.stringify(editedData, null, 2)}
          </pre>
        </div>
      </div>
    );
  };

  const renderAIAvatar = useCallback(() => {
    return (
      <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-blue-500 via-purple-500 to-indigo-600 rounded-full flex items-center justify-center mr-3 shadow-lg">
        <span className="text-white text-sm font-bold">🤖</span>
      </div>
    );
  }, []);

  // Memoized message rendering to prevent flickering
  const renderMessageContent = useCallback((message) => {
    const formatTimestamp = (timestamp) => {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
      <div className={`flex ${message.isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`max-w-3xl ${message.isUser ? 'order-2' : 'order-1'}`}>
          <div className={`message-bubble p-4 rounded-xl shadow-lg ${
            message.isUser 
              ? 'bg-gradient-to-br from-blue-600 to-purple-600 text-white ml-auto' 
              : message.isSystem 
                ? 'bg-cyan-900/30 border border-cyan-500/30 text-cyan-100'
                : message.isEdit
                  ? 'bg-green-900/30 border border-green-500/30 text-green-100'
                  : message.isWelcome
                    ? 'bg-gradient-to-br from-purple-900/40 to-blue-900/40 border border-purple-500/30 text-purple-100'
                    : message.isGmailSuccess
                      ? 'bg-transparent border-0 p-0' // Special styling for Gmail success
                      : 'bg-gray-800/40 backdrop-blur-sm border border-gray-600/30 text-white'
          }`}>
            {!message.isUser && (
              <div className="flex items-start space-x-3">
                {!message.isGmailSuccess && renderAIAvatar()}
                <div className="flex-1">
                  {message.isGmailSuccess ? (
                    renderGmailSuccessMessage()
                  ) : message.intent_data?.intent === 'generate_post_prompt_package' ? (
                    // Only show the card format for post prompt packages
                    renderPostPromptPackage(message)
                  ) : (
                    <div className="chat-message">
                      <ReactMarkdown>
                        {message.response ? renderEmailDisplay(message.response) : message.message}
                      </ReactMarkdown>
                    </div>
                  )}
                  {renderIntentData(message.intent_data)}
                  <div className="text-xs opacity-70 mt-2">
                    {formatTimestamp(message.timestamp)}
                  </div>
                </div>
              </div>
            )}

            {message.isUser && (
              <div>
                <div className="chat-message">
                  <ReactMarkdown>
                    {message.message}
                  </ReactMarkdown>
                </div>
                <div className="text-xs opacity-70 mt-2">
                  {formatTimestamp(message.timestamp)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }, [renderEmailDisplay, renderAIAvatar, renderGmailSuccessMessage, renderPostPromptPackage, renderIntentData]);

  return (
    <div className="flex flex-col h-full">
      {/* Chat Messages - Scrollable Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-blue-500/50 scrollbar-track-transparent">
        {messages.map((message) => (
          <div key={message.id}>
            {renderMessageContent(message)}
          </div>
        ))}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="max-w-3xl">
              <div className="message-bubble p-4 rounded-xl bg-gray-800/40 backdrop-blur-sm border border-gray-600/30">
                <div className="flex items-start space-x-3">
                  {renderAIAvatar()}
                  <div className="flex-1">
                    <div className="loading-dots">
                      <div className="loading-dot bg-blue-400"></div>
                      <div className="loading-dot bg-blue-500"></div>
                      <div className="loading-dot bg-blue-600"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 🔒 Admin Debug Toggle - Only visible for admin emails */}
      {showAdminToggle && (
        <div className="admin-toggle-container px-4 pb-2">
          <div className="max-w-4xl mx-auto">
            <button
              onClick={toggleAdminMode}
              className={`admin-debug-toggle ${isAdminMode ? 'active' : ''}`}
              title={isAdminMode ? 'Admin Mode: ON' : 'Admin Mode: OFF'}
            >
              <span className="toggle-icon">🔐</span>
              <span className="toggle-text">
                {isAdminMode ? 'Admin Debug: ON' : 'Admin Debug: OFF'}
              </span>
              <div className={`toggle-indicator ${isAdminMode ? 'active' : ''}`}>
                <div className="toggle-slider"></div>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Message Input - Fixed at Bottom */}
      <div className="chat-input-container p-4">
        <div className="max-w-4xl mx-auto">
          <div className="glassy-input-area rounded-xl p-4 flex items-center space-x-3">
            {/* Show automation status if available */}
            {automationStatus && (
              <div className="automation-status">
                <span className="shimmer-text">{automationStatus}</span>
              </div>
            )}
            
            <div className="flex-1 flex items-center space-x-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Ask me anything... ✨"
                className="flex-1 clean-input"
                disabled={isLoading}
              />
              
              <button
                onClick={sendMessage}
                disabled={isLoading || !inputMessage.trim()}
                className="premium-new-chat-btn px-6 py-3 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              >
                {isLoading ? (
                  <div className="loading-dots">
                    <div className="loading-dot bg-blue-400"></div>
                    <div className="loading-dot bg-blue-500"></div>
                    <div className="loading-dot bg-blue-600"></div>
                  </div>
                ) : (
                  'Send'
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Approval Modal */}
      {showApprovalModal && pendingApproval && (
        <AnimatePresence mode="wait">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="approval-modal-backdrop fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="approval-modal-content bg-gray-800 rounded-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto border border-gray-600 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white flex items-center">
                  <span className="mr-2">🤖</span>
                  Action Approval Required
                </h3>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setEditMode(!editMode)}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                  >
                    {editMode ? 'View' : 'Edit'}
                  </button>
                </div>
              </div>

              <div className="mb-4 p-3 bg-blue-900/20 rounded-lg border border-blue-500/30">
                <p className="text-sm text-blue-300 mb-2">
                  ⚠️ This action was generated by AI. Please review the details before approving.
                </p>
                <div className="text-sm text-gray-300">
                  <strong>Detected Intent:</strong> {pendingApproval.intent_data?.intent?.replace('_', ' ').toUpperCase()}
                </div>
              </div>

              {editMode ? (
                renderEditForm()
              ) : (
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-blue-300 flex items-center">
                    <span className="mr-2">📋</span>
                    Action Details:
                  </h4>
                  <div className="bg-gray-900/40 p-4 rounded-lg border border-gray-600/30">
                    <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                      {JSON.stringify(editedData || pendingApproval.intent_data, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => handleApproval(false)}
                  className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleApproval(true)}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  Approve
                </button>
              </div>
            </motion.div>
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}

export default ChatBox;