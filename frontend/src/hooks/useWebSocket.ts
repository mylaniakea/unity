import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface UseWebSocketOptions {
  url?: string;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  subscribeTo?: {
    plugin_ids?: string[];
    metric_names?: string[];
  };
}

export interface UseWebSocketReturn {
  connected: boolean;
  send: (message: object) => void;
  subscribe: (pluginIds?: string[], metricNames?: string[]) => void;
  unsubscribe: (pluginIds?: string[], metricNames?: string[]) => void;
  reconnect: () => void;
  lastMessage: WebSocketMessage | null;
  error: Event | null;
}

/**
 * React hook for WebSocket connections with auto-reconnect and subscription support
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = `ws://${window.location.hostname}:8000/ws/metrics`,
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    subscribeTo,
  } = options;

  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<Event | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        onConnect?.();

        // Subscribe if options provided
        if (subscribeTo) {
          ws.send(JSON.stringify({
            type: 'subscribe',
            plugin_ids: subscribeTo.plugin_ids || [],
            metric_names: subscribeTo.metric_names || [],
          }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError(event);
        onError?.(event);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        onDisconnect?.();

        // Attempt to reconnect if we should
        if (shouldReconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          console.log(`Reconnecting... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error('Max reconnection attempts reached');
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setError(err as Event);
    }
  }, [url, onMessage, onError, onConnect, onDisconnect, reconnectInterval, maxReconnectAttempts, subscribeTo]);

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, []);

  const subscribe = useCallback((pluginIds?: string[], metricNames?: string[]) => {
    send({
      type: 'subscribe',
      plugin_ids: pluginIds || [],
      metric_names: metricNames || [],
    });
  }, [send]);

  const unsubscribe = useCallback((pluginIds?: string[], metricNames?: string[]) => {
    send({
      type: 'unsubscribe',
      plugin_ids: pluginIds || [],
      metric_names: metricNames || [],
    });
  }, [send]);

  const reconnect = useCallback(() => {
    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    if (wsRef.current) {
      wsRef.current.close();
    }
    connect();
  }, [connect]);

  useEffect(() => {
    connect();
    shouldReconnectRef.current = true;

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    connected,
    send,
    subscribe,
    unsubscribe,
    reconnect,
    lastMessage,
    error,
  };
}

