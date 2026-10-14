import { useCallback, useEffect, useState } from 'react';
import { fetchHealth, fetchReadiness } from '../api/health';
import type { HealthResponse, ReadinessResponse } from '../types';

export function useHealth(pollIntervalMs = 8000) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = useCallback(async () => {
    try {
      const [h, r] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchReadiness().catch((err: unknown) => {
          if (
            err instanceof Error &&
            'details' in err &&
            typeof err.details === 'object' &&
            err.details !== null &&
            'services' in err.details
          ) {
            return err.details as ReadinessResponse;
          }

          return null;
        }),
      ]);

      if (!h) {
        setError(
          'Backend API is unreachable. Please verify server is running.',
        );
        setHealth(null);
        setReadiness(null);
      } else {
        setError(null);
        setHealth(h);
        setReadiness(r);
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : 'Backend check failed',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialCheck = window.setTimeout(() => {
      void checkStatus();
    }, 0);

    const interval = window.setInterval(() => {
      void checkStatus();
    }, pollIntervalMs);

    return () => {
      window.clearTimeout(initialCheck);
      window.clearInterval(interval);
    };
  }, [checkStatus, pollIntervalMs]);

  return {
    health,
    readiness,
    loading,
    error,
    refresh: checkStatus,
  };
}