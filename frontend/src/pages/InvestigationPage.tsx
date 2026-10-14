import React, { useCallback, useEffect, useState } from 'react';
import {
  ArrowLeft,
  ShieldAlert,
  RefreshCw,
  AlertCircle,
  Clock,
  FileSearch,
  Network,
  AlertTriangle,
  Info,
  CheckCircle2,
  CircleHelp,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import type { Investigation } from '../types';
import { fetchInvestigationById } from '../api/investigations';

interface InvestigationPageProps {
  investigationId: string;
  initialData?: Investigation | null;
  onBack: () => void;
}

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const getString = (value: unknown): string | null =>
  typeof value === 'string' && value.trim() ? value.trim() : null;

const getDisplayValue = (value: unknown): string => {
  if (typeof value === 'string') return value;

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  if (value == null) return 'Not provided';

  try {
    return JSON.stringify(value, null, 2) ?? 'Value cannot be displayed';
  } catch {
    return 'Value cannot be displayed';
  }
};

const formatDate = (value: string | undefined): string => {
  if (!value) return 'Not available';

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? 'Not available'
    : date.toLocaleString();
};

const normalizeStatus = (status: unknown): string =>
  typeof status === 'string' && status.trim()
    ? status.trim().toUpperCase().replace(/[\s-]+/g, '_')
    : 'UNKNOWN';

const formatStatus = (status: unknown): string =>
  normalizeStatus(status).replace(/[_-]+/g, ' ').toLowerCase();

const getStatusStyle = (status: unknown): string => {
  switch (normalizeStatus(status)) {
    case 'SUCCESS':
      return 'border-emerald-800 bg-emerald-950/30 text-emerald-300';
    case 'PARTIAL':
    case 'NOT_VERIFIED':
    case 'INSUFFICIENT_EVIDENCE':
      return 'border-amber-800 bg-amber-950/30 text-amber-300';
    case 'FAILED':
      return 'border-rose-800 bg-rose-950/30 text-rose-300';
    case 'UNAVAILABLE':
      return 'border-gray-700 bg-gray-900 text-gray-400';
    case 'PENDING':
    case 'CREATED':
      return 'border-blue-800 bg-blue-950/30 text-blue-300';
    default:
      return 'border-gray-700 bg-gray-900 text-gray-300';
  }
};

const getState = (investigation: Investigation): UnknownRecord =>
  isRecord(investigation.state) ? investigation.state : {};

const getArray = (state: UnknownRecord, key: string): unknown[] =>
  Array.isArray(state[key]) ? state[key] as unknown[] : [];

const getSummary = (investigation: Investigation): string | null => {
  const summary = getString(investigation.result_summary);

  if (summary) return summary;

  const analysis = getState(investigation).scam_pattern_analysis;

  if (isRecord(analysis)) {
    return getString(analysis.explanation) ?? getString(analysis.summary);
  }

  return null;
};

const getToolResults = (investigation: Investigation): unknown[] => {
  const results = getState(investigation).tool_results;

  if (Array.isArray(results)) return results;

  if (isRecord(results)) {
    return Object.entries(results).map(([toolName, result]) => {
      if (isRecord(result)) {
        return { ...result, tool_name: toolName };
      }

      return { tool_name: toolName, output_summary: result };
    });
  }

  return [];
};

const getFindings = (investigation: Investigation): unknown[] => {
  const state = getState(investigation);

  return [
    ...getArray(state, 'indicators').map((item) => ({
      ...(isRecord(item) ? item : { value: item }),
      finding_category: 'Indicator',
    })),
    ...getArray(state, 'claims').map((item) => ({
      ...(isRecord(item) ? item : { value: item }),
      finding_category: 'Claim',
    })),
  ];
};

const getEntities = (investigation: Investigation): unknown[] =>
  getArray(getState(investigation), 'entities');

const getEvidence = (investigation: Investigation): unknown[] =>
  Array.isArray(investigation.evidence) ? investigation.evidence : [];

const getMessages = (investigation: Investigation): unknown[] =>
  getArray(getState(investigation), 'messages');

const getErrors = (investigation: Investigation): unknown[] =>
  getArray(getState(investigation), 'errors');

const getWarnings = (investigation: Investigation): unknown[] =>
  getArray(getState(investigation), 'warnings');

const getRiskExplanation = (investigation: Investigation): string | null => {
  const analysis = getState(investigation).scam_pattern_analysis;

  if (!isRecord(analysis)) return null;

  return getString(analysis.explanation) ?? getString(analysis.summary);
};

const getConfidenceDisplay = (value: number): string => {
  const percentage = value >= 0 && value <= 1 ? value * 100 : value;

  return Number.isFinite(percentage)
    ? `${percentage.toFixed(1)}%`
    : 'Not available';
};

const DetailValue: React.FC<{
  label: string;
  value: unknown;
}> = ({ label, value }) => (
  <div className="min-w-0">
    <p className="mb-1 text-xs text-gray-500">{label}</p>
    <p className="break-words text-sm text-gray-200">
      {getDisplayValue(value)}
    </p>
  </div>
);

const DataCard: React.FC<{
  item: unknown;
  index: number;
  title?: string;
}> = ({ item, index, title }) => {
  const record = isRecord(item) ? item : { value: item };

  const heading =
    title ??
    getString(record.name) ??
    getString(record.tool_name) ??
    getString(record.claim) ??
    getString(record.description) ??
    `Item ${index + 1}`;

  const ignoredKeys = new Set([
    'id',
    'investigation_id',
    'input_id',
    'raw_payload',
    'name',
    'tool_name',
    'claim',
    'description',
  ]);

  const entries = Object.entries(record).filter(
    ([key, value]) =>
      !ignoredKeys.has(key) &&
      value !== undefined &&
      value !== null &&
      value !== '',
  );

  return (
    <article className="min-w-0 rounded-xl border border-gray-800 bg-gray-900/50 p-4">
      <h4 className="break-words text-sm font-semibold text-gray-100">
        {heading}
      </h4>

      {entries.length > 0 ? (
        <div className="mt-3 space-y-3">
          {entries.map(([key, value]) => {
            if (key === 'status') {
              return (
                <div key={key} className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-gray-500">Status</span>
                  <span
                    className={`inline-flex rounded-md border px-2 py-1 text-xs ${getStatusStyle(value)}`}
                  >
                    {formatStatus(value)}
                  </span>
                </div>
              );
            }

            if (key === 'confidence' && typeof value === 'number') {
              return (
                <div key={key}>
                  <p className="mb-1 text-xs text-gray-500">
                    Evidence / extraction confidence
                  </p>
                  <p className="text-sm text-gray-200">
                    {getConfidenceDisplay(value)}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    This is not a probability that fraud occurred.
                  </p>
                </div>
              );
            }

            return (
              <DetailValue
                key={key}
                label={key.replace(/[_-]+/g, ' ')}
                value={value}
              />
            );
          })}
        </div>
      ) : (
        <p className="mt-2 text-xs text-gray-500">
          No additional details were returned.
        </p>
      )}
    </article>
  );
};

export const InvestigationPage: React.FC<InvestigationPageProps> = ({
  investigationId,
  initialData,
  onBack,
}) => {
  const [investigation, setInvestigation] = useState<Investigation | null>(
    initialData?.id === investigationId ? initialData : null,
  );

  const [loading, setLoading] = useState(
    initialData?.id !== investigationId,
  );

  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadInvestigation = useCallback(
    async (showLoading = true) => {
      if (showLoading) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError(null);

      try {
        const data = await fetchInvestigationById(investigationId);

        if (!isRecord(data) || typeof data.id !== 'string' || !data.id) {
          throw new Error('The API returned an invalid investigation record.');
        }

        setInvestigation(data);
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? err.message
            : 'Failed to fetch the investigation record.',
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [investigationId],
  );

  useEffect(() => {
    if (initialData?.id === investigationId) return;

    const timeoutId = window.setTimeout(() => {
      void loadInvestigation(true);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [investigationId, initialData, loadInvestigation]);

  const activeInvestigation =
    initialData?.id === investigationId ? initialData : investigation;

  const state = activeInvestigation ? getState(activeInvestigation) : {};
  const evidence = activeInvestigation ? getEvidence(activeInvestigation) : [];
  const entities = activeInvestigation ? getEntities(activeInvestigation) : [];
  const findings = activeInvestigation ? getFindings(activeInvestigation) : [];
  const toolResults = activeInvestigation ? getToolResults(activeInvestigation) : [];
  const errors = activeInvestigation ? getErrors(activeInvestigation) : [];
  const warnings = activeInvestigation ? getWarnings(activeInvestigation) : [];
  const messages = activeInvestigation ? getMessages(activeInvestigation) : [];
  const summary = activeInvestigation ? getSummary(activeInvestigation) : null;
  const riskExplanation = activeInvestigation
    ? getRiskExplanation(activeInvestigation)
    : null;

  const status = activeInvestigation
    ? normalizeStatus(activeInvestigation.status)
    : 'UNKNOWN';

  const isPending = ['CREATED', 'PENDING'].includes(status);
  const hasToolFailures = toolResults.some(
    (item) =>
      isRecord(item) &&
      ['FAILED', 'UNAVAILABLE'].includes(normalizeStatus(item.status)),
  );

  const reportNotice = (() => {
    if (status === 'PARTIAL') {
      return {
        title: 'Partial investigation results',
        description:
          'Some analysis stages may have failed or returned incomplete data. Review the tool results and warnings before drawing conclusions.',
        style: 'border-amber-800 bg-amber-950/20 text-amber-200',
      };
    }

    if (status === 'FAILED') {
      return {
        title: 'Investigation failed',
        description:
          'The API reports that this investigation failed. Any returned evidence is retained for review, but a complete analysis is not available.',
        style: 'border-rose-800 bg-rose-950/20 text-rose-200',
      };
    }

    if (status === 'UNAVAILABLE') {
      return {
        title: 'Analysis unavailable',
        description:
          'The API reports that analysis is unavailable. No successful verification should be inferred from this result.',
        style: 'border-gray-700 bg-gray-900 text-gray-300',
      };
    }

    if (status === 'NOT_VERIFIED') {
      return {
        title: 'Not verified',
        description:
          'The available data does not establish that this content has been verified.',
        style: 'border-amber-800 bg-amber-950/20 text-amber-200',
      };
    }

    if (status === 'INSUFFICIENT_EVIDENCE') {
      return {
        title: 'Insufficient evidence',
        description:
          'There is not enough returned evidence to support a reliable conclusion.',
        style: 'border-amber-800 bg-amber-950/20 text-amber-200',
      };
    }

    if (hasToolFailures) {
      return {
        title: 'Some analysis tools did not complete',
        description:
          'One or more tool results report a failure or unavailable status. Review the available evidence and tool errors.',
        style: 'border-amber-800 bg-amber-950/20 text-amber-200',
      };
    }

    return null;
  })();

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <button
        type="button"
        onClick={onBack}
        className="mb-6 inline-flex items-center gap-2 text-xs font-semibold text-gray-400 transition hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </button>

      {loading && !activeInvestigation && (
        <div
          role="status"
          className="rounded-2xl border border-gray-800 bg-[#101726] p-12 text-center"
        >
          <RefreshCw className="mx-auto mb-3 h-8 w-8 animate-spin text-blue-400" />
          <p className="text-sm text-gray-400">Loading investigation record...</p>
        </div>
      )}

      {!loading && !activeInvestigation && error && (
        <div
          role="alert"
          className="rounded-2xl border border-rose-800 bg-rose-950/40 p-6 text-rose-300"
        >
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-rose-400" />
            <div>
              <h3 className="font-bold text-white">Investigation Lookup Failed</h3>
              <p className="mt-1 break-words text-sm text-rose-300/80">{error}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void loadInvestigation(true)}
            className="mt-4 rounded-lg bg-rose-900/60 px-4 py-2 text-xs font-semibold text-white transition hover:bg-rose-800"
          >
            Retry Fetch
          </button>
        </div>
      )}

      {activeInvestigation && (
        <div className="space-y-8">
          <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 shadow-xl shadow-black/40 sm:p-8">
            <div className="flex flex-col justify-between gap-4 border-b border-gray-800 pb-6 sm:flex-row sm:items-center">
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-3">
                  <h1 className="break-words text-xl font-bold text-white sm:text-2xl">
                    {activeInvestigation.title || 'Untitled Fraud Investigation'}
                  </h1>
                  <StatusBadge status={activeInvestigation.status} />
                </div>

                <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-gray-400">
                  <span>ID:</span>
                  <span className="break-all text-blue-400 select-all">
                    {activeInvestigation.id}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span className="rounded-lg border border-gray-800 bg-gray-900 px-3 py-1.5 font-mono">
                  v{activeInvestigation.vera_version || 'unknown'}
                </span>
                <button
                  type="button"
                  onClick={() => void loadInvestigation(false)}
                  disabled={refreshing}
                  className="rounded-lg border border-gray-800 bg-gray-900 p-2 transition hover:text-white disabled:opacity-50"
                  title="Refresh investigation record"
                  aria-label="Refresh investigation record"
                >
                  <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {activeInvestigation.description && (
              <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
                {activeInvestigation.description}
              </p>
            )}

            <div className="mt-6 grid grid-cols-2 gap-4 border-t border-gray-800/80 pt-6 text-xs sm:grid-cols-4">
              <DetailValue label="Status" value={formatStatus(activeInvestigation.status)} />
              <DetailValue label="Created At" value={formatDate(activeInvestigation.created_at)} />
              <DetailValue label="Updated At" value={formatDate(activeInvestigation.updated_at)} />
              <DetailValue label="Engine" value={activeInvestigation.vera_version || 'VERA Core'} />
            </div>

            {error && (
              <div
                role="alert"
                className="mt-5 rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-sm text-amber-300"
              >
                Refresh failed: {error}. Previously loaded results are still displayed.
              </div>
            )}
          </section>

          {reportNotice && (
            <section
              role="status"
              className={`rounded-xl border p-5 ${reportNotice.style}`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <h2 className="font-semibold">{reportNotice.title}</h2>
                  <p className="mt-1 text-sm opacity-90">{reportNotice.description}</p>
                </div>
              </div>
            </section>
          )}

          {isPending && (
            <section className="rounded-xl border border-blue-800 bg-blue-950/20 p-5">
              <div className="flex items-start gap-3">
                <Clock className="mt-0.5 h-5 w-5 text-blue-400" />
                <div>
                  <h2 className="font-semibold text-blue-200">Investigation pending</h2>
                  <p className="mt-1 text-sm text-gray-400">
                    The API currently reports this investigation as {formatStatus(status)}.
                    Refresh the record to check for updated results.
                  </p>
                  <button
                    type="button"
                    onClick={() => void loadInvestigation(false)}
                    disabled={refreshing}
                    className="mt-3 inline-flex items-center gap-2 text-sm text-blue-300 hover:text-white disabled:opacity-50"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Refresh status
                  </button>
                </div>
              </div>
            </section>
          )}

          <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
            <div className="mb-4 flex items-center gap-2">
              <FileSearch className="h-5 w-5 text-blue-400" />
              <h2 className="text-lg font-bold text-white">Investigation Summary</h2>
            </div>

            {summary ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
                {summary}
              </p>
            ) : (
              <div className="rounded-lg border border-dashed border-gray-700 p-5">
                <p className="text-sm text-gray-400">No investigation summary was returned by the API.</p>
                <p className="mt-1 text-xs text-gray-500">
                  This does not mean the submitted content is safe.
                </p>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-bold text-white">
                <ShieldAlert className="h-5 w-5 text-blue-400" />
                Claims &amp; Indicators
              </h2>
              <span className="rounded border border-gray-700 bg-gray-900 px-2.5 py-1 text-xs text-gray-300">
                {findings.length} items
              </span>
            </div>

            {findings.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {findings.map((item, index) => (
                  <DataCard key={index} item={item} index={index} />
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-gray-700 p-5">
                <div className="flex items-start gap-3">
                  <CircleHelp className="mt-0.5 h-5 w-5 text-gray-500" />
                  <div>
                    <p className="text-sm text-gray-300">No claims or indicators returned</p>
                    <p className="mt-1 text-xs text-gray-500">
                      This may mean extraction was unavailable or the API returned no findings.
                      Review tool results and warnings before interpreting this as a clean result.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-bold text-white">
                <Network className="h-5 w-5 text-blue-400" />
                Extracted Entities
              </h2>
              <span className="rounded border border-gray-700 bg-gray-900 px-2.5 py-1 text-xs text-gray-300">
                {entities.length} entities
              </span>
            </div>

            {entities.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {entities.map((item, index) => (
                  <DataCard key={index} item={item} index={index} />
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-gray-700 p-5">
                <div className="flex items-start gap-3">
                  <Network className="mt-0.5 h-5 w-5 text-gray-500" />
                  <div>
                    <p className="text-sm text-gray-300">No extracted entities returned</p>
                    <p className="mt-1 text-xs text-gray-500">
                      An entity relationship graph cannot be rendered without entity and relationship
                      data from the API. No relationships have been inferred or fabricated.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-white">Evidence &amp; Provenance</h2>
                <p className="mt-1 text-xs text-gray-400">
                  Evidence returned by the investigation API
                </p>
              </div>
              <span className="rounded border border-blue-800/50 bg-blue-950 px-2.5 py-1 text-xs text-blue-300">
                {evidence.length} artifacts
              </span>
            </div>

            {evidence.length > 0 ? (
              <div className="space-y-4">
                {evidence.map((item, index) => (
                  <DataCard
                    key={index}
                    item={item}
                    index={index}
                    title={
                      isRecord(item)
                        ? getString(item.description) ??
                          getString(item.type) ??
                          `Evidence ${index + 1}`
                        : `Evidence ${index + 1}`
                    }
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-gray-700 p-6 text-center">
                <Info className="mx-auto mb-3 h-7 w-7 text-gray-500" />
                <p className="text-sm font-medium text-gray-300">No evidence artifacts returned</p>
                <p className="mt-1 text-xs text-gray-500">
                  The API response contains no evidence artifacts to display. This is not confirmation
                  that the content is safe.
                </p>
              </div>
            )}
          </section>

          {riskExplanation && (
            <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
              <h2 className="mb-3 text-lg font-bold text-white">Pattern Analysis Explanation</h2>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
                {riskExplanation}
              </p>
              <p className="mt-3 text-xs text-gray-500">
                This explanation reflects returned pattern analysis. It is not, by itself, a verified
                fraud determination or numeric risk score.
              </p>
            </section>
          )}

          <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
            <h2 className="mb-5 text-lg font-bold text-white">Analysis Tool Results</h2>

            {toolResults.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {toolResults.map((item, index) => (
                  <DataCard key={index} item={item} index={index} />
                ))}
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-gray-700 p-5 text-sm text-gray-400">
                No tool execution records were included in the API response.
              </p>
            )}
          </section>

          {(warnings.length > 0 || errors.length > 0) && (
            <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
              <h2 className="mb-5 flex items-center gap-2 text-lg font-bold text-white">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                Warnings &amp; Errors
              </h2>

              <div className="space-y-4">
                {warnings.map((item, index) => (
                  <div
                    key={`warning-${index}`}
                    className="rounded-lg border border-amber-800/70 bg-amber-950/20 p-4"
                  >
                    <p className="mb-1 text-xs uppercase tracking-wide text-amber-400">Warning</p>
                    <p className="break-words text-sm text-gray-300">{getDisplayValue(item)}</p>
                  </div>
                ))}

                {errors.map((item, index) => (
                  <div
                    key={`error-${index}`}
                    className="rounded-lg border border-rose-800/70 bg-rose-950/20 p-4"
                  >
                    <p className="mb-1 text-xs uppercase tracking-wide text-rose-400">Error</p>
                    <p className="break-words text-sm text-gray-300">{getDisplayValue(item)}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {messages.length > 0 && (
            <section className="rounded-2xl border border-gray-800 bg-[#101726] p-6 sm:p-8">
              <h2 className="mb-5 text-lg font-bold text-white">Investigation Activity</h2>
              <div className="space-y-3">
                {messages.map((item, index) => (
                  <DataCard key={index} item={item} index={index} />
                ))}
              </div>
            </section>
          )}

          {Object.keys(state).length === 0 && (
            <div className="rounded-xl border border-gray-700 bg-gray-900/50 p-4 text-sm text-gray-400">
              <p className="font-medium text-gray-300">Detailed analysis state is unavailable</p>
              <p className="mt-1">
                The investigation record was loaded, but the API did not return a detailed state object.
                Only fields present in the response can be displayed.
              </p>
            </div>
          )}

          <div className="flex flex-col gap-3 text-xs text-gray-500 sm:flex-row sm:items-center sm:justify-between">
            <span>Results are based on the investigation record returned by the backend.</span>
            <button
              type="button"
              onClick={() => void loadInvestigation(false)}
              disabled={refreshing}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-700 px-4 py-2 transition hover:border-gray-500 hover:text-white disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh results
            </button>
          </div>

          {status === 'SUCCESS' && !hasToolFailures && (
            <p className="flex items-center gap-2 text-xs text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              The investigation API reports successful completion. Review the evidence above
              before drawing conclusions.
            </p>
          )}
        </div>
      )}
    </div>
  );
};