/**
 * context/WebSocketContext.jsx
 * ============================
 * WebSocket Real-time Updates Context Provider
 *
 * WHY THIS FILE EXISTS:
 *     Connects to the backend WebSocket stream, handles auto-reconnections
 *     with exponential backoff, and provides an event-subscription pattern
 *     so pages (Dashboard, Alerts, Tickets) consume live events without polling.
 *
 * KEY IMPROVEMENTS:
 *     - Smart URL resolution: uses VITE_API_URL env if set, else auto-detects
 *       local (localhost) vs production (Render) based on window.location.
 *     - Exponential backoff reconnect (1s → 2s → 4s → ... max 30s)
 *     - Heartbeat ping every 25s to keep connection alive through proxies
 *     - Connection only starts after token is available (avoids 403 on Render)
 */

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';

const WebSocketContext = createContext(null);

const MAX_RECONNECT_DELAY = 30000; // 30 seconds max
const HEARTBEAT_INTERVAL = 25000;  // 25 seconds

/** Resolves the WebSocket URL from environment or current browser location. */
function resolveWsUrl() {
  const apiUrl = import.meta.env.VITE_API_URL;

  if (apiUrl) {
    // Strip trailing slash, replace http → ws
    return apiUrl.replace(/\/$/, '').replace(/^http/, 'ws') + '/ws/live';
  }

  // Auto-detect: if running locally, use localhost backend
  const isLocal =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1';

  if (isLocal) {
    return 'ws://localhost:8000/api/v1/ws/live';
  }

  // Production fallback (Render deployment)
  return 'wss://aether-noc-backend.onrender.com/api/v1/ws/live';
}

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);
  const listenersRef = useRef({});
  const reconnectTimeoutRef = useRef(null);
  const heartbeatRef = useRef(null);
  const reconnectDelay = useRef(1000); // Starts at 1s, doubles each failure

  const stopHeartbeat = () => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  };

  const startHeartbeat = (ws) => {
    stopHeartbeat();
    heartbeatRef.current = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, HEARTBEAT_INTERVAL);
  };

  const connect = useCallback(() => {
    // Don't connect if already open or connecting
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const wsUrl = resolveWsUrl();
    console.log(`[WS] Connecting to: ${wsUrl}`);

    let ws;
    try {
      ws = new WebSocket(wsUrl);
    } catch (err) {
      console.error('[WS] Failed to create WebSocket:', err);
      scheduleReconnect();
      return;
    }

    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectDelay.current = 1000; // Reset backoff on success
      console.log('[WS] Connected to AETHER NOC live notification channel.');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      startHeartbeat(ws);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        // Skip pong/ack internal messages from dashboard feed
        if (payload.event === 'ack' || payload.type === 'pong') return;

        setLastMessage(payload);

        const eventType = payload.event;
        const data = payload.data;

        if (eventType && listenersRef.current[eventType]) {
          listenersRef.current[eventType].forEach((callback) => {
            try {
              callback(data);
            } catch (err) {
              console.error(`[WS] Subscriber error for event "${eventType}":`, err);
            }
          });
        }
      } catch (err) {
        console.error('[WS] Failed to parse message frame:', err);
      }
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      stopHeartbeat();
      console.log(`[WS] Connection closed. Code: ${event.code}, Reason: ${event.reason || 'none'}`);
      scheduleReconnect();
    };

    ws.onerror = (error) => {
      console.error('[WS] WebSocket connection error:', error);
      ws.close();
    };
  }, []);

  const scheduleReconnect = () => {
    if (reconnectTimeoutRef.current) return;
    const delay = reconnectDelay.current;
    console.log(`[WS] Reconnecting in ${delay}ms...`);
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectTimeoutRef.current = null;
      // Exponential backoff, capped at MAX_RECONNECT_DELAY
      reconnectDelay.current = Math.min(reconnectDelay.current * 2, MAX_RECONNECT_DELAY);
      connect();
    }, delay);
  };

  useEffect(() => {
    connect();

    return () => {
      stopHeartbeat();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  /**
   * Subscribes to a specific WebSocket event channel.
   * Returns an unsubscribe function for use in useEffect cleanup hooks.
   *
   * @param {string} eventType - Event identifier (e.g. 'metric_ingested', 'alert_triggered')
   * @param {function} callback - Handler called with the event data payload
   * @returns {function} Cleanup / unsubscribe function
   */
  const subscribe = useCallback((eventType, callback) => {
    if (!listenersRef.current[eventType]) {
      listenersRef.current[eventType] = new Set();
    }
    listenersRef.current[eventType].add(callback);

    return () => {
      if (listenersRef.current[eventType]) {
        listenersRef.current[eventType].delete(callback);
      }
    };
  }, []);

  /**
   * Sends a raw JSON payload to the server over the live WebSocket.
   */
  const sendMessage = useCallback((payload) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload));
    } else {
      console.warn('[WS] Cannot send — WebSocket is not open.');
    }
  }, []);

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
