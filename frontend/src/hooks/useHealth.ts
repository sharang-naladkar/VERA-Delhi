import { useEffect, useState } from 'react';
import { fetchHealth, fetchReadiness } from '../api/health';
import { HealthResponse, ReadinessResponse } from '../types';

export function useHealth(pollIntervalMs = 8000) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = async () => {
    try {
      const [h, r] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchReadiness().catch((err) => {
          if (err.details && typeof err.details === 'object' && 'services' in err.details) {
            return err.details as ReadinessResponse;
          }
          return null;
        }),
      ]);

      if (!h) {
        setError('Backend API is unreachable. Please verify server is running.');
        setHealth(null);
        setReadiness(null);
      } else {
        setError(null);
        setHealth(h);
        setReadiness(r);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Backend check failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, pollIntervalMs);
    return () => clearInterval(interval);
  }, [pollIntervalMs]);

  return { health, readiness, loading, error, refresh: checkStatus };
}
