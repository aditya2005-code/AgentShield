'use client';

import { useState, useEffect, useCallback } from 'react';
import { getHealthStatus } from '../lib/api/client';

export type HealthStatus = 'checking' | 'connected' | 'unavailable';

export function useApiHealth() {
  const [status, setStatus] = useState<HealthStatus>('checking');
  const [day, setDay] = useState<number | null>(null);

  const checkHealth = useCallback(async () => {
    setStatus('checking');
    try {
      const data = await getHealthStatus();
      if (data && data.status === 'healthy' && data.database === 'connected') {
        setStatus('connected');
        if (data.day !== undefined) {
          setDay(data.day);
        }
      } else {
        setStatus('unavailable');
      }
    } catch (err) {
      setStatus('unavailable');
    }
  }, []);

  useEffect(() => {
    checkHealth();

    // Sparse check: run once every 30 seconds to maintain status in the UI
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return {
    status,
    day,
    checkHealth
  };
}
