import React from 'react';

const Message = ({ message, animationDelay }) => {
  const isUser = message.sender === 'user';
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // Show intent data if available
  const showIntentInfo = message.intent_data && message.intent_data.intent !== 'general_chat';

  return (
    <div 
      className={`message ${isUser ? 'user-message' : 'ai-message'}`}
      style={{ animationDelay: `${animationDelay}s` }}
    >
      <div className="message-content">
        <div className="message-bubble">
          <p>{message.text}</p>
          {showIntentInfo && (
            <div className="intent-info">
              <div className="intent-badge">
                🎯 Intent: {message.intent_data.intent}
              </div>
              {message.intent_data.intent === 'send_email' && (
                <div className="email-details">
                  {message.intent_data.recipient_name && (
                    <div className="detail">📧 To: {message.intent_data.recipient_name}</div>
                  )}
                  {message.intent_data.subject && (
                    <div className="detail">📝 Subject: {message.intent_data.subject}</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
        <div className="message-time">
          {formatTime(message.timestamp)}
        </div>
      </div>
      {!isUser && <div className="ai-avatar">AI</div>}
    </div>
  );
};

export default Message;