import React from 'react';
import Message from './Message';
import TypingIndicator from './TypingIndicator';

const MessageList = ({ messages, isTyping }) => {
  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <Message 
          key={message.id} 
          message={message} 
          animationDelay={index * 0.1}
        />
      ))}
      {isTyping && <TypingIndicator />}
    </div>
  );
};

export default MessageList;