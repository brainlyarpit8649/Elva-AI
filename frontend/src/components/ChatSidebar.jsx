import React, { useState, useEffect } from 'react';
import chatService from '../services/chatService';
import { useToast } from '../hooks/use-toast';
import './ChatSidebar.css';

const ChatSidebar = ({ currentSessionId, onSessionSelect, onNewChat }) => {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadChatSessions();
  }, []);

  const loadChatSessions = async () => {
    try {
      setIsLoading(true);
      const sessionList = await chatService.getAllSessions();
      setSessions(sessionList);
    } catch (error) {
      console.error('Error loading chat sessions:', error);
      toast({
        title: "Error",
        description: "Failed to load chat history.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    onNewChat();
    loadChatSessions(); // Refresh sessions after creating new chat
  };

  const formatSessionTitle = (session) => {
    if (session.title) return session.title;
    
    // Generate title from first message or timestamp
    const date = new Date(session.created_at);
    const timeAgo = getTimeAgo(date);
    return `Chat ${timeAgo}`;
  };

  const getTimeAgo = (date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return date.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className={`chat-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <button 
            className="toggle-btn"
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            {isCollapsed ? '→' : '←'}
          </button>
          {!isCollapsed && <h2>Chat History</h2>}
        </div>
        <div className="sidebar-loading">
          <div className="loading-spinner-small"></div>
          {!isCollapsed && <span>Loading...</span>}
        </div>
      </div>
    );
  }

  return (
    <div className={`chat-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <button 
          className="toggle-btn"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? '→' : '←'}
        </button>
        {!isCollapsed && <h2>Chat History</h2>}
      </div>
      
      {!isCollapsed && (
        <>
          <button className="new-chat-btn" onClick={handleNewChat}>
            <span className="plus-icon">+</span>
            New Chat
          </button>
          
          <div className="sessions-list">
            {sessions.length === 0 ? (
              <div className="empty-state">
                <p>No chat history yet</p>
                <span>Start your first conversation!</span>
              </div>
            ) : (
              sessions.map(session => (
                <div
                  key={session.id}
                  className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
                  onClick={() => onSessionSelect(session.id)}
                >
                  <div className="session-content">
                    <div className="session-title">
                      {formatSessionTitle(session)}
                    </div>
                    <div className="session-meta">
                      <span className="message-count">{session.message_count || 0} messages</span>
                      <span className="session-time">{getTimeAgo(new Date(session.last_activity))}</span>
                    </div>
                  </div>
                  <div className="session-indicator"></div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ChatSidebar;