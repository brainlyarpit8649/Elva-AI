import React, { useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const GmailAuthHandler = ({ 
  gmailAuthStatus, 
  setGmailAuthStatus, 
  sessionId, 
  setMessages,
  checkGmailStatus // Receive the parent status check function
}) => {
  
  const checkGmailAuthStatus = async () => {
    // Use the parent function if available, otherwise fallback to local implementation
    if (checkGmailStatus) {
      return await checkGmailStatus();
    }
    
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
        
        // Add helpful debug message to chat
        const debugMessage = {
          id: 'gmail_debug_' + Date.now(),
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
        
        // Only add debug message if we don't have one already
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

  const initiateGmailAuth = async () => {
    try {
      const response = await axios.get(`${API}/gmail/auth?session_id=${sessionId}`);
      if (response.data.success && response.data.auth_url) {
        // Add session ID to the auth URL state parameter
        const authUrl = new URL(response.data.auth_url);
        const currentState = authUrl.searchParams.get('state') || '';
        authUrl.searchParams.set('state', `${sessionId}_${currentState}`);
        
        // Redirect to Google OAuth2 with session-aware state
        window.location.href = authUrl.toString();
      } else {
        console.error('Failed to get Gmail auth URL:', response.data.message);
      }
    } catch (error) {
      console.error('Gmail auth initiation failed:', error);
    }
  };

  const handleGmailAuthSuccess = async () => {
    try {
      // Update auth status using the parent function or fallback
      if (checkGmailStatus) {
        await checkGmailStatus();
      } else {
        await checkGmailAuthStatus();
      }
      
      // Add success message to chat with special formatting
      const successMessage = {
        id: 'gmail_auth_success_' + Date.now(),
        session_id: sessionId,
        user_id: 'system',
        message: '✅ Gmail OAuth2 Flow Completed!',
        response: '🎉 **Gmail Connected Successfully!**\n\n' +
          '✅ Authentication completed\n' +
          '📧 You can now ask me to:\n' +
          '• Check your Gmail inbox\n' +
          '• Send emails\n' +
          '• Read specific emails\n' +
          '• Search your messages\n\n' +
          '💡 The status badge above shows your connection is live and active!',
        timestamp: new Date().toISOString(),
        intent_data: null,
        needs_approval: false,
        isGmailSuccess: true // Special flag for custom rendering
      };
      
      setMessages(prev => [...prev, successMessage]);
      
      console.log('Gmail authentication successful - status updated!');
    } catch (error) {
      console.error('Error handling Gmail auth success:', error);
    }
  };

  const handleGmailAuthError = (errorMessage, details) => {
    try {
      // Update auth status and re-check using parent function or fallback
      if (checkGmailStatus) {
        checkGmailStatus();
      } else {
        checkGmailAuthStatus();
      }
      
      // Map error codes to user-friendly messages
      let userMessage = 'Gmail authentication failed. Please try again.';
      let debugInfo = details || '';
      
      switch(errorMessage) {
        case 'access_denied':
          userMessage = 'Gmail authentication was cancelled. You can try connecting again anytime.';
          debugInfo = 'User denied access during OAuth2 flow.';
          break;
        case 'no_code':
          userMessage = 'Gmail authentication failed - no authorization received.';
          debugInfo = 'OAuth2 callback did not receive authorization code.';
          break;
        case 'auth_failed':
          userMessage = 'Gmail authentication failed during token exchange.';
          debugInfo = details || 'Token exchange with Google failed.';
          break;
        case 'server_error':
          userMessage = 'Gmail authentication failed due to a server error.';
          debugInfo = details || 'Backend server error during OAuth2 processing.';
          break;
        default:
          debugInfo = details || `Unknown error: ${errorMessage}`;
      }
      
      console.error('🚨 Gmail Auth Error Details:', { errorMessage, details, debugInfo });
      
      // Add error message to chat with debug info
      const errorMsg = {
        id: 'gmail_auth_error_' + Date.now(),
        session_id: sessionId,
        user_id: 'system', 
        message: '❌ Gmail Authentication Failed',
        response: `❌ **Gmail Authentication Error**\n\n${userMessage}\n\n` +
                 `🔧 **Debug Info**: ${debugInfo}\n` +
                 `🆔 **Session**: ${sessionId}\n\n` +
                 `💡 **Next Steps**: Check the "Connect Gmail" button above shows the correct status, or try the authentication flow again.`,
        timestamp: new Date().toISOString(),
        intent_data: null,
        needs_approval: false
      };
      
      setMessages(prev => [...prev, errorMsg]);
      
      console.error('Gmail authentication error processed');
    } catch (error) {
      console.error('Error handling Gmail auth error:', error);
    }
  };

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
      // Gmail authentication successful
      console.log('✅ Processing Gmail auth success');
      handleGmailAuthSuccess();
      // Clear URL parameters
      window.history.replaceState({}, document.title, '/');
    } else if (auth === 'error') {
      // Gmail authentication failed
      console.error('❌ Processing Gmail auth error:', message, details);
      handleGmailAuthError(message, details);
      // Clear URL parameters  
      window.history.replaceState({}, document.title, '/');
    }
  }, []);

  return {
    checkGmailAuthStatus,
    initiateGmailAuth,
    handleGmailAuthSuccess,
    handleGmailAuthError
  };
};

export default GmailAuthHandler;