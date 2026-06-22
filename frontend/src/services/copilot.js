/**
 * services/copilot.js
 * ===================
 * API Client Integration for the AI Copilot Assistant
 * Includes support for persistent chat session CRUD operations and SSE streaming.
 */

import api from './api';

export const copilotService = {
  /**
   * Retrieves list of recent chat sessions for the logged-in user.
   */
  listSessions: async () => {
    const response = await api.get('/copilot/sessions');
    return response.data;
  },

  /**
   * Creates a new chat session.
   */
  createSession: async (title) => {
    const response = await api.post('/copilot/sessions', { title });
    return response.data;
  },

  /**
   * Deletes a chat session and its history logs.
   */
  deleteSession: async (sessionId) => {
    await api.delete(`/copilot/sessions/${sessionId}`);
  },

  /**
   * Loads message history thread for a session.
   */
  getSessionHistory: async (sessionId) => {
    const response = await api.get(`/copilot/sessions/${sessionId}/history`);
    return response.data;
  },

  /**
   * Streams chat messages token-by-token using standard fetch + SSE stream reader.
   */
  streamChat: async (sessionId, query, onChunk, onError, onDone) => {
    const token = localStorage.getItem('token');
    const apiUrl = import.meta.env.VITE_API_URL || https://aether-noc-backend.onrender.com;

    try {
      const response = await fetch(`${apiUrl}/copilot/sessions/${sessionId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ query })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || 'Failed to initiate chatbot session.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last incomplete line in the buffer
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              if (data.error) {
                onError(data.error);
              } else if (data.content !== undefined) {
                onChunk(data.content);
              }
            } catch (err) {
              console.error('Failed to parse SSE data stream line:', trimmed, err);
            }
          }
        }
      }
      onDone();
    } catch (err) {
      onError(err.message || err);
    }
  }
};

export default copilotService;
