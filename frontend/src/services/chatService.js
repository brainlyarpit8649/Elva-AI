import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

class ChatService {
  constructor() {
    this.sessionId = this.getOrCreateSessionId();
    this.userId = 'anonymous';
  }

  getOrCreateSessionId() {
    let sessionId = localStorage.getItem('elva_session_id');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('elva_session_id', sessionId);
    }
    return sessionId;
  }

  setSessionId(sessionId) {
    this.sessionId = sessionId;
    localStorage.setItem('elva_session_id', sessionId);
  }

  async sendMessage(message) {
    try {
      const response = await axios.post(`${API}/chat/message`, {
        session_id: this.sessionId,
        user_id: this.userId,
        message: message
      });
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  async getChatHistory(limit = 50) {
    try {
      const response = await axios.get(`${API}/chat/history/${this.sessionId}?limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error('Error getting chat history:', error);
      throw error;
    }
  }

  async createSession() {
    try {
      const response = await axios.post(`${API}/chat/session?user_id=${this.userId}`);
      this.sessionId = response.data.id;
      localStorage.setItem('elva_session_id', this.sessionId);
      return response.data;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error;
    }
  }

  async getSession() {
    try {
      const response = await axios.get(`${API}/chat/session/${this.sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting session:', error);
      throw error;
    }
  }

  async getAllSessions() {
    try {
      const response = await axios.get(`${API}/chat/sessions?user_id=${this.userId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting all sessions:', error);
      throw error;
    }
  }

  async deleteSession(sessionId) {
    try {
      const response = await axios.delete(`${API}/chat/session/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting session:', error);
      throw error;
    }
  }
}

export default new ChatService();