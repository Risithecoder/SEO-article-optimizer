import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/ws`;

export default function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [steps, setSteps] = useState([]);
  const [logs, setLogs] = useState([]);
  const [pipelineComplete, setPipelineComplete] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'initial_state':
          setSteps(data.status?.steps || []);
          setLogs(data.logs || []);
          break;

        case 'step_update':
          setSteps((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((s) => s.id === data.step_id);
            if (idx >= 0) {
              updated[idx] = { ...updated[idx], status: data.status, detail: data.detail };
            }
            return updated;
          });
          break;

        case 'log':
          setLogs((prev) => [...prev.slice(-499), { timestamp: data.timestamp, level: data.level, message: data.message }]);
          break;

        case 'pipeline_complete':
          setPipelineComplete(true);
          break;

        case 'heartbeat':
          break;

        default:
          break;
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { connected, steps, logs, pipelineComplete, setPipelineComplete };
}
