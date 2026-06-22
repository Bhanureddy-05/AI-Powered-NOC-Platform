/**
 * context/WebSocketContext.jsx
 * ============================
 * WebSocket Real-time Updates Context Provider
 * 
 * WHY THIS FILE EXISTS:
 *     Connects to the backend WebSocket stream, handles auto-reconnections,
 *     and provides an event-subscription pattern so pages (Dashboard, Alerts, Tickets)
 *     can consume live events without polling or page refreshes.
 */

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);
  const listenersRef = useRef({}); // Maps event -> Set of callback functions
  const reconnectTimeoutRef = useRef(null);

  const connect = () => {
    // Resolve WS protocol based on API base URL
    const apiUrl = import.meta.env.VITE_API_URL || wss://aether-noc-backend.onrender.com;
    const wsUrl = apiUrl.replace(/^http/, 'ws') + '/ws/live';

    console.log(`[WS] Connecting to: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log('[WS] Connected to live NOC platform notification channel.');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setLastMessage(payload);

        const eventType = payload.event;
        const data = payload.data;

        // Notify all subscribers of this event category
        if (eventType && listenersRef.current[eventType]) {
          listenersRef.current[eventType].forEach((callback) => {
            try {
              callback(data);
            } catch (err) {
              console.error(`[WS] Subscriber error for event ${eventType}:`, err);
            }
          });
        }
      } catch (err) {
        console.error('[WS] Failed to parse message frame:', err);
      }
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      console.log('[WS] WebSocket connection closed. Code:', event.code);
      // Auto-reconnect with 3-second delay
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('[WS] WebSocket encountered connection error:', error);
      ws.close();
    };
  };

  useEffect(() => {
    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  /**
   * Subscribes to a specific event broadcast channel.
   * Returns a cleanup function to unsubscribe.
   * 
   * @param {string} eventType - The string identifier of the event (e.g. 'metric_ingested', 'alert_triggered')
   * @param {function} callback - Callback function execution receiving payload data
   */
  const subscribe = (eventType, callback) => {
    if (!listenersRef.current[eventType]) {
      listenersRef.current[eventType] = new Set();
    }
    listenersRef.current[eventType].add(callback);

    // Return cleanup hook
    return () => {
      if (listenersRef.current[eventType]) {
        listenersRef.current[eventType].delete(callback);
      }
    };
  };

  /**
   * Sends a payload message up to the server.
   */
  const sendMessage = (payload) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload));
    } else {
      console.warn('[WS] Cannot send message. WebSocket is not open.');
    }
  };

  return (
    <WebSocketContext.Provider value={{ isConnected, lastMessage, subscribe, sendMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export default WebSocketContext;
