import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { HomePage } from '../src/pages/HomePage';
import { InvestigationPage } from '../src/pages/InvestigationPage';
import {
  createInvestigation,
  fetchInvestigationById,
} from '../src/api/investigations';
import type {
  HealthResponse,
  ReadinessResponse,
  Investigation,
} from '../src/types';

vi.mock('../src/api/investigations', () => ({
  createInvestigation: vi.fn(),
  fetchInvestigationById: vi.fn(),
}));

const readyHealth: HealthResponse = {
  status: 'ok',
  version: 'test',
  timestamp: '2025-01-01T00:00:00Z',
};

const readyReadiness: ReadinessResponse = {
  status: 'ready',
  timestamp: '2025-01-01T00:00:00Z',
  services: {
    database: {
      status: 'ready',
      message: 'Available',
      latency_ms: 1,
    },
    redis: {
      status: 'ready',
      message: 'Available',
      latency_ms: 1,
    },
    minio: {
      status: 'ready',
      message: 'Available',
      latency_ms: 1,
    },
  },
};

const mockInvestigation = {
  id: 'test-investigation-id',
  title: 'Test investigation',
  description: 'Test description',
  status: 'SUCCESS',
  vera_version: 'test',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  evidence_count: 1,
  result_summary: 'Suspicious activity detected.',
  evidence: [
    {
      id: 'evidence-1',
      type: 'text',
      description: 'Suspicious message',
      confidence: 0.9,
      source_type: 'user_input',
    },
  ],
  state: {
    entities: [{ name: 'Example Company', type: 'organization' }],
    claims: [{ claim: 'A suspicious claim', status: 'SUCCESS' }],
    indicators: [{ name: 'Suspicious indicator', severity: 'high' }],
    warnings: ['Some tools were unavailable.'],
    errors: [],
    tool_results: [],
    messages: [],
  },
} satisfies Investigation;

describe('Investigation workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits supplied text to the API', async () => {
    const created = { ...mockInvestigation };
    vi.mocked(createInvestigation).mockResolvedValue(created);

    const onOpenInvestigation = vi.fn();

    render(
      <HomePage
        health={readyHealth}
        readiness={readyReadiness}
        healthError={null}
        onOpenInvestigation={onOpenInvestigation}
      />,
    );

    fireEvent.change(
      screen.getByLabelText(/suspicious content to investigate/i),
      {
        target: {
          value: 'Please investigate this suspicious message.',
        },
      },
    );

    fireEvent.click(
      screen.getByRole('button', { name: /start investigation/i }),
    );

    await waitFor(() => {
      expect(createInvestigation).toHaveBeenCalledWith(
        expect.objectContaining({
          text: 'Please investigate this suspicious message.',
          input_type: 'text',
        }),
      );
    });

    await waitFor(() => {
      expect(onOpenInvestigation).toHaveBeenCalledWith(created);
    });
  });

  it('rejects empty investigation text', () => {
    render(
      <HomePage
        health={readyHealth}
        readiness={readyReadiness}
        healthError={null}
        onOpenInvestigation={vi.fn()}
      />,
    );

    const input = screen.getByLabelText(
      /suspicious content to investigate/i,
    );

    expect(input).toBeRequired();
    expect(input).toHaveValue('');
    expect(createInvestigation).not.toHaveBeenCalled();
  });

  it('shows API errors and preserves submitted input', async () => {
    vi.mocked(createInvestigation).mockRejectedValue(
      new Error('API unavailable'),
    );

    render(
      <HomePage
        health={readyHealth}
        readiness={readyReadiness}
        healthError={null}
        onOpenInvestigation={vi.fn()}
      />,
    );

    const input = screen.getByLabelText(
      /suspicious content to investigate/i,
    );

    fireEvent.change(input, {
      target: {
        value: 'Keep this text after an API error.',
      },
    });

    fireEvent.click(
      screen.getByRole('button', { name: /start investigation/i }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /API unavailable/i,
    );

    expect(input).toHaveValue('Keep this text after an API error.');
  });

  it('renders the investigation summary and evidence', async () => {
    vi.mocked(fetchInvestigationById).mockResolvedValue(
      mockInvestigation,
    );

    render(
      <InvestigationPage
        investigationId={mockInvestigation.id}
        onBack={vi.fn()}
      />,
    );

    expect(
      await screen.findByText('Suspicious activity detected.'),
    ).toBeInTheDocument();

    expect(
      screen.getByText('Evidence & Provenance'),
    ).toBeInTheDocument();

    expect(screen.getByText('Suspicious message')).toBeInTheDocument();
  });

  it('renders partial results and warnings', async () => {
    const partialInvestigation: Investigation = {
      ...mockInvestigation,
      status: 'PARTIAL',
      state: {
        ...mockInvestigation.state,
        warnings: ['Some tools were unavailable.'],
      },
    };

    vi.mocked(fetchInvestigationById).mockResolvedValue(
      partialInvestigation,
    );

    render(
      <InvestigationPage
        investigationId={partialInvestigation.id}
        onBack={vi.fn()}
      />,
    );

    expect(
      await screen.findByText('Some tools were unavailable.'),
    ).toBeInTheDocument();
  });

  it('shows an error when fetching an investigation fails', async () => {
    vi.mocked(fetchInvestigationById).mockRejectedValue(
      new Error('Unable to reach investigation API'),
    );

    render(
      <InvestigationPage
        investigationId="missing-investigation"
        onBack={vi.fn()}
      />,
    );

    expect(
      await screen.findByText('Unable to reach investigation API'),
    ).toBeInTheDocument();
  });
});