import React from 'react';

const TypingIndicator = () => {
  return (
    <div className="message ai-message typing-indicator">
      <div className="message-content">
        <div className="message-bubble">
          <div className="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
      <div className="ai-avatar">AI</div>
    </div>
  );
};

export default TypingIndicator;