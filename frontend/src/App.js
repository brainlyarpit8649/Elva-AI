import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import TypewriterTagline from './TypewriterTagline';
import ChatBox from './ChatBox';
import DropdownMenu from './DropdownMenu';
import GmailAuthHandler from './GmailAuthHandler';
import { exportChatToPDFEnhanced, exportChatToPDF } from './utils/pdfExport';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(generateSessionId());
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    // Initialize theme from localStorage or default to dark
    const savedTheme = localStorage.getItem('elva-theme');
    return savedTheme ? savedTheme === 'dark' : true;
  }); // Theme toggle state with localStorage persistence
  const [gmailAuthStatus, setGmailAuthStatus] = useState({ 
    authenticated: false, 
    loading: true, 
    credentialsConfigured: false,
    error: null,
    debugInfo: null 
  }); // Gmail authentication status
  const [showDropPanel, setShowDropPanel] = useState(false); // Drop-left panel state

  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  // Initialize theme on app load
  useEffect(() => {
    const savedTheme = localStorage.getItem('elva-theme');
    const isInitiallyDark = savedTheme ? savedTheme === 'dark' : true;
    
    if (isInitiallyDark) {
      document.documentElement.classList.add('dark-theme');
      document.documentElement.classList.remove('light-theme');
    } else {
      document.documentElement.classList.add('light-theme');
      document.documentElement.classList.remove('dark-theme');
    }
  }, []);

  useEffect(() => {
    loadChatHistory();
    // Add welcome message when starting a new chat
    if (messages.length === 0) {
      addWelcomeMessage();
    }
  }, [sessionId]);

  const addWelcomeMessage = () => {
    const baseMessage = "Hi Buddy 👋 Good to see you! Elva AI at your service. Ask me anything or tell me what to do!";
    const gmailMessage = gmailAuthStatus.authenticated 
      ? "\n\n🎉 **Gmail is connected!** I can now help you with:\n• 📧 Check your Gmail inbox\n• ✉️ Send emails\n• 📨 Read specific emails\n• 🔍 Search your messages"
      : "\n\n💡 **Tip:** Connect Gmail above for email assistance!";
    
    const welcomeMessage = {
      id: 'welcome_' + Date.now(),
      response: baseMessage + gmailMessage,
      isUser: false,
      isWelcome: true,
      timestamp: new Date()
    };
    setMessages([welcomeMessage]);
  };

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/history/${sessionId}`);
      const historyMessages = response.data.messages || [];
      if (historyMessages.length === 0) {
        addWelcomeMessage();
      } else {
        setMessages(historyMessages.map(msg => ({
          ...msg,
          isUser: false, // History messages are from AI
          timestamp: new Date(msg.timestamp)
        })));
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
      addWelcomeMessage();
    }
  };

  const startNewChat = () => {
    setSessionId(generateSessionId());
    setMessages([]);
    setShowDropPanel(false); // Close panel when starting new chat
  };

  // Theme toggle function with localStorage persistence
  const toggleTheme = () => {
    const newTheme = !isDarkTheme;
    setIsDarkTheme(newTheme);
    
    // Save theme preference to localStorage
    localStorage.setItem('elva-theme', newTheme ? 'dark' : 'light');
    
    // Apply theme changes to document
    if (newTheme) {
      // Dark theme
      document.documentElement.classList.remove('light-theme');
      document.documentElement.classList.add('dark-theme');
    } else {
      // Light theme
      document.documentElement.classList.remove('dark-theme');
      document.documentElement.classList.add('light-theme');
    }
  };

  // Enhanced PDF export function
  const exportChat = () => {
    try {
      console.log('📤 Exporting chat to PDF...', messages.length, 'messages');
      
      // Try enhanced export first, fallback to basic if needed
      const result = exportChatToPDFEnhanced(messages);
      
      if (result.success) {
        console.log('✅ PDF export successful:', result.fileName);
        
        // Add success message to chat
        const successMsg = {
          id: 'export_success_' + Date.now(),
          response: `📄 **Chat exported successfully!**\n\n` +
                   `📁 **File**: ${result.fileName}\n` +
                   `📊 **Messages**: ${result.messageCount} messages exported\n` +
                   `✨ **Format**: ${result.enhanced ? 'Enhanced PDF with chat bubbles' : 'Standard PDF'}\n\n` +
                   `The file has been downloaded to your device. You can find it in your Downloads folder.`,
          isUser: false,
          isSystem: true,
          timestamp: new Date()
        };
        
        setMessages(prev => [...prev, successMsg]);
      } else {
        console.error('❌ PDF export failed:', result.error);
        
        // Add error message to chat
        const errorMsg = {
          id: 'export_error_' + Date.now(),
          response: `❌ **Export failed**\n\n` +
                   `Sorry, there was an issue exporting your chat to PDF: ${result.error}\n\n` +
                   `Please try again or contact support if the issue persists.`,
          isUser: false,
          isSystem: true,
          timestamp: new Date()
        };
        
        setMessages(prev => [...prev, errorMsg]);
      }
      
      setShowDropPanel(false); // Close panel after export
      
    } catch (error) {
      console.error('❌ PDF export module loading failed:', error);
      
      // Fallback to basic text export if PDF fails completely
      const chatData = messages
        .filter(msg => !msg.isSystem)
        .map(msg => {
          const timestamp = msg.timestamp ? new Date(msg.timestamp).toLocaleString() : '';
          const sender = msg.isUser ? 'You' : 'Elva AI';
          const content = msg.message || msg.response || '';
          return `[${timestamp}] ${sender}: ${content}`;
        })
        .join('\n\n');
      
      const blob = new Blob([chatData], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `elva-chat-${new Date().toISOString().split('T')[0]}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      // Add fallback message
      const fallbackMsg = {
        id: 'export_fallback_' + Date.now(),
        response: `📄 **Chat exported as text file**\n\n` +
                 `PDF export encountered an issue, so your chat has been saved as a text file instead.\n` +
                 `Check your Downloads folder for: elva-chat-${new Date().toISOString().split('T')[0]}.txt`,
        isUser: false,
        isSystem: true,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, fallbackMsg]);
      setShowDropPanel(false);
    }
  };

  // Initialize Gmail auth handler
  const gmailAuthHandler = GmailAuthHandler({ 
    gmailAuthStatus, 
    setGmailAuthStatus, 
    sessionId, 
    setMessages 
  });

  return (
    <div className="chat-background h-screen text-white flex flex-col overflow-hidden">
      {/* Premium Glassy Header */}
      <header className="glassy-header shadow-lg flex-shrink-0">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between relative z-10">
          <div className="flex items-center space-x-4">
            <div className="logo-container">
              <img 
                src="/logo.svg" 
                alt="Elva AI Logo" 
                className="elva-logo"
                onError={(e) => {
                  // Fallback to gradient logo if image fails to load
                  e.target.style.display = 'none';
                  e.target.nextElementSibling.style.display = 'flex';
                }}
              />
              {/* Fallback gradient logo */}
              <div 
                className="w-12 h-12 bg-gradient-to-br from-blue-500 via-purple-500 to-indigo-600
                         rounded-full flex items-center justify-center text-white font-bold text-xl shadow-lg"
                style={{ display: 'none' }}
              >
                E
              </div>
            </div>
            <div>
              <h1 className="text-3xl font-bold smooth-glow-title">Elva AI</h1>
              <TypewriterTagline />
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Drop-Left Panel with 3D Buttons */}
            <DropdownMenu
              showDropPanel={showDropPanel}
              setShowDropPanel={setShowDropPanel}
              toggleTheme={toggleTheme}
              isDarkTheme={isDarkTheme}
              exportChat={exportChat}
              startNewChat={startNewChat}
            />

            {/* Gmail Button in Header */}
            <button
              onClick={gmailAuthStatus.authenticated ? null : gmailAuthHandler.initiateGmailAuth}
              className={`circular-icon-btn ${
                gmailAuthStatus.authenticated 
                  ? 'gmail-connected' 
                  : gmailAuthStatus.credentialsConfigured 
                    ? 'gmail-ready' 
                    : 'gmail-error'
              }`}
              title={
                gmailAuthStatus.authenticated 
                  ? "Gmail Connected ✅" 
                  : gmailAuthStatus.credentialsConfigured 
                    ? "Connect Gmail" 
                    : "Gmail credentials missing ❌"
              }
              disabled={gmailAuthStatus.authenticated || !gmailAuthStatus.credentialsConfigured}
            >
              <div className="connected-indicator">
                <img 
                  src="https://images.unsplash.com/photo-1706879349268-8cb3a9ae739a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzd8MHwxfHNlYXJjaHwxfHxnbWFpbCUyMGxvZ298ZW58MHx8fHwxNzUzMjQ4NTQ1fDA&ixlib=rb-4.1.0&q=85"
                  alt="Gmail"
                  className="gmail-icon"
                />
                {gmailAuthStatus.authenticated && (
                  <div className="connected-check">✓</div>
                )}
              </div>
            </button>
          </div>
        </div>
      </header>

      {/* Chat Container - Proper Flex Layout */}
      <main className="premium-chat-container">
        <ChatBox
          sessionId={sessionId}
          gmailAuthStatus={gmailAuthStatus}
          setGmailAuthStatus={setGmailAuthStatus}
          messages={messages}
          setMessages={setMessages}
        />
      </main>
    </div>
  );
}

export default App;