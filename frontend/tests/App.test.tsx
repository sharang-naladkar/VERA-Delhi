import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../src/App';
import * as healthApi from '../src/api/health';

describe('VERA Frontend Application', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders application header and title', async () => {
    vi.spyOn(healthApi, 'fetchHealth').mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      timestamp: new Date().toISOString(),
    });

    vi.spyOn(healthApi, 'fetchReadiness').mockResolvedValue({
      status: 'ready',
      timestamp: new Date().toISOString(),
      services: {
        database: { status: 'ready', message: 'DB OK', latency_ms: 1.0 },
        redis: { status: 'ready', message: 'Redis OK', latency_ms: 0.5 },
        minio: { status: 'ready', message: 'MinIO OK', latency_ms: 1.2 },
      },
    });

    render(<App />);

    expect(screen.getAllByText(/VERA/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Start New Investigation/i)).toBeInTheDocument();

    await waitFor(() => {
      const onlineBadges = screen.getAllByText(/Online/i);
      expect(onlineBadges.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('displays connection warning when backend health check fails', async () => {
    vi.spyOn(healthApi, 'fetchHealth').mockRejectedValue(new Error('Network error'));
    vi.spyOn(healthApi, 'fetchReadiness').mockRejectedValue(new Error('Network error'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Connection Warning/i)).toBeInTheDocument();
      expect(screen.getByText(/Backend API is unreachable/i)).toBeInTheDocument();
    });
  });
});
