import React from 'react';

const Message = ({ message, animationDelay }) => {
  const isUser = message.sender === 'user';
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div 
      className={`message ${isUser ? 'user-message' : 'ai-message'}`}
      style={{ animationDelay: `${animationDelay}s` }}
    >
      <div className="message-content">
        <div className="message-bubble">
          <p>{message.text}</p>
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