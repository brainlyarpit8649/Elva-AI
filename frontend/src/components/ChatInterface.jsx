import React, { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import chatService from '../services/chatService';
import { useToast } from '../hooks/use-toast';
import './ChatInterface.css';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load chat history on component mount
    loadChatHistory();
  }, []);

  const loadChatHistory = async () => {
    try {
      setIsLoading(true);
      const history = await chatService.getChatHistory();
      
      // Transform backend response to frontend format
      const formattedMessages = history.map(msg => ({
        id: msg.id,
        text: msg.message,
        sender: msg.sender,
        timestamp: msg.timestamp,
        intent_data: msg.intent_data
      }));
      
      setMessages(formattedMessages);
      
      // If no history, show welcome message
      if (formattedMessages.length === 0) {
        const welcomeMessage = {
          id: `welcome_${Date.now()}`,
          text: "Hello! I'm Elva AI, your intelligent assistant. I can help you with various tasks like sending emails and more. How can I assist you today?",
          sender: 'ai',
          timestamp: new Date().toISOString()
        };
        setMessages([welcomeMessage]);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
      toast({
        title: "Error",
        description: "Failed to load chat history. Please refresh the page.",
        variant: "destructive"
      });
      
      // Show welcome message even if history loading fails
      const welcomeMessage = {
        id: `welcome_${Date.now()}`,
        text: "Hello! I'm Elva AI, your intelligent assistant. I can help you with various tasks like sending emails and more. How can I assist you today?",
        sender: 'ai',
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (messageText) => {
    // Add user message to UI immediately
    const userMessage = {
      id: `user_${Date.now()}`,
      text: messageText,
      sender: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    try {
      // Send message to backend
      const response = await chatService.sendMessage(messageText);
      
      // Add AI response to UI
      const aiMessage = {
        id: response.id,
        text: response.message,
        sender: 'ai',
        timestamp: response.timestamp,
        intent_data: response.intent_data
      };
      
      setMessages(prev => [...prev, aiMessage]);
      
      // Show success toast if email intent was detected
      if (response.intent_data?.intent === 'send_email') {
        toast({
          title: "Email Intent Detected",
          description: "I've detected you want to send an email. Processing your request...",
          variant: "default"
        });
      }
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message to UI
      const errorMessage = {
        id: `error_${Date.now()}`,
        text: "I'm sorry, I encountered an error processing your message. Please try again.",
        sender: 'ai',
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, errorMessage]);
      
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsTyping(false);
    }
  };

  if (isLoading) {
    return (
      <div className="chat-interface">
        <div className="chat-header">
          <div className="ai-status">
            <div className="status-indicator"></div>
            <h1 className="ai-name">Elva AI</h1>
          </div>
          <div className="header-glow"></div>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading chat history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="ai-status">
          <div className="status-indicator"></div>
          <h1 className="ai-name">Elva AI</h1>
        </div>
        <div className="header-subtitle">
          <p>Intelligent Assistant • Intent Detection • Email Automation</p>
        </div>
        <div className="header-glow"></div>
      </div>
      
      <div className="chat-container">
        <MessageList messages={messages} isTyping={isTyping} />
        <div ref={messagesEndRef} />
      </div>
      
      <MessageInput onSendMessage={handleSendMessage} />
    </div>
  );
};

export default ChatInterface;