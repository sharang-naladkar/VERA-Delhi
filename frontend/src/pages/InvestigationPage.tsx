import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Cpu,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { Investigation, RiskAssessment } from '../types';
import { fetchInvestigationById } from '../api/investigations';

interface InvestigationPageProps {
  investigationId: string;
  initialData?: Investigation | null;
  onBack: () => void;
}

const riskStyles: Record<
  RiskAssessment['level'],
  { panel: string; text: string; bar: string }
> = {
  low: {
    panel: 'border-emerald-800/70 bg-emerald-950/20',
    text: 'text-emerald-300',
    bar: 'bg-emerald-500',
  },
  medium: {
    panel: 'border-amber-800/70 bg-amber-950/20',
    text: 'text-amber-300',
    bar: 'bg-amber-500',
  },
  high: {
    panel: 'border-orange-800/70 bg-orange-950/20',
    text: 'text-orange-300',
    bar: 'bg-orange-500',
  },
  critical: {
    panel: 'border-rose-800/70 bg-rose-950/20',
    text: 'text-rose-300',
    bar: 'bg-rose-500',
  },
};

export const InvestigationPage: React.FC<InvestigationPageProps> = ({
  investigationId,
  initialData,
  onBack,
}) => {
  const [investigation, setInvestigation] = useState<Investigation | null>(
    initialData || null
  );
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);

  const loadInvestigation = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchInvestigationById(investigationId);
      setInvestigation(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch investigation');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData) {
      loadInvestigation();
    }
  }, [investigationId]);

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 text-xs font-semibold text-gray-400 hover:text-white mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </button>

        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-800 text-rose-300">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-rose-400" />
            <div>
              <h3 className="font-bold text-white">Investigation Lookup Failed</h3>
              <p className="text-xs mt-1">{error}</p>
            </div>
          </div>

          <button
            onClick={loadInvestigation}
            className="mt-4 px-4 py-2 bg-rose-900/60 hover:bg-rose-800 text-white rounded-lg text-xs font-semibold"
          >
            Retry Fetch
          </button>
        </div>
      </div>
    );
  }

  if (loading || !investigation) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="p-12 text-center bg-[#101726] border border-gray-800 rounded-2xl">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-400">
            Loading investigation record...
          </p>
        </div>
      </div>
    );
  }

  const risk = investigation.state?.risk_assessment;
  const evidence = investigation.evidence || [];
  const riskLevel = risk?.level;
  const riskStyle = riskLevel ? riskStyles[riskLevel] : null;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-2 text-xs font-semibold text-gray-400 hover:text-white mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </button>

      <div className="space-y-6">
        {/* Header */}
        <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-black/40">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <h1 className="text-xl sm:text-2xl font-bold text-white">
                  {investigation.title || 'Untitled Fraud Investigation'}
                </h1>
                <StatusBadge status={investigation.status} />
              </div>

              <div className="text-xs text-gray-400 font-mono">
                ID:{' '}
                <span className="text-blue-400 select-all">
                  {investigation.id}
                </span>
              </div>
            </div>

            <button
              onClick={loadInvestigation}
              className="self-start p-2 rounded-lg bg-gray-900 border border-gray-800 hover:text-white"
              title="Refresh record"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {investigation.description && (
            <p className="text-sm text-gray-300 mt-5 leading-relaxed">
              {investigation.description}
            </p>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-800">
            <div>
              <span className="text-gray-500 block mb-1 text-xs">Status</span>
              <span className="font-semibold text-gray-200 text-sm capitalize">
                {investigation.status}
              </span>
            </div>

            <div>
              <span className="text-gray-500 block mb-1 text-xs">
                Evidence
              </span>
              <span className="font-semibold text-gray-200 text-sm">
                {investigation.evidence_count ?? evidence.length}
              </span>
            </div>

            <div>
              <span className="text-gray-500 block mb-1 text-xs">
                Created
              </span>
              <span className="font-mono text-gray-300 text-xs">
                {new Date(investigation.created_at).toLocaleString()}
              </span>
            </div>

            <div>
              <span className="text-gray-500 block mb-1 text-xs">Engine</span>
              <span className="font-semibold text-blue-400 text-sm">
                VERA Core
              </span>
            </div>
          </div>
        </div>

        {/* Risk Assessment */}
        {risk ? (
          <div
            className={`rounded-2xl border p-6 sm:p-8 ${riskStyle?.panel || 'border-gray-800 bg-[#101726]'}`}
          >
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <ShieldAlert className={`w-5 h-5 ${riskStyle?.text}`} />
                  <h2 className="text-lg font-bold text-white">
                    Deterministic Risk Assessment
                  </h2>
                </div>

                <p className="text-xs text-gray-400 max-w-xl">
                  Risk is calculated from structured evidence and verified
                  investigation signals. It is not an LLM-generated fraud
                  probability.
                </p>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className={`text-4xl font-extrabold ${riskStyle?.text}`}>
                    {risk.score}
                  </div>
                  <div className="text-[11px] uppercase tracking-wider text-gray-500">
                    Risk Index / 100
                  </div>
                </div>

                <div className="text-left">
                  <StatusBadge
                    status={risk.level}
                    label={risk.level.toUpperCase()}
                  />
                  <div className="text-[11px] text-gray-500 mt-1">
                    Assessment {risk.status}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <div className="h-2 rounded-full bg-gray-900 overflow-hidden">
                <div
                  className={`h-full rounded-full ${riskStyle?.bar || 'bg-gray-500'}`}
                  style={{
                    width: `${Math.min(Math.max(risk.score, 0), 100)}%`,
                  }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-[#101726] border border-amber-800/60 rounded-2xl p-6">
            <div className="flex items-center gap-3">
              <TriangleAlert className="w-5 h-5 text-amber-400" />
              <div>
                <h2 className="text-sm font-bold text-white">
                  Risk Assessment Unavailable
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  No deterministic risk assessment was persisted for this
                  investigation. This is not interpreted as low risk.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Risk Signals */}
        {risk && risk.signals.length > 0 && (
          <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8">
            <div className="flex items-center gap-2 mb-5">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
              <div>
                <h2 className="text-lg font-bold text-white">
                  Risk Signals
                </h2>
                <p className="text-xs text-gray-400">
                  Deterministic contributions to the risk index
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {risk.signals.map((signal) => (
                <div
                  key={signal.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-gray-900/60 border border-gray-800"
                >
                  <div>
                    <p className="text-sm font-semibold text-gray-200">
                      {signal.category.replace(/_/g, ' ')}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {signal.description}
                    </p>
                    <p className="text-[11px] text-gray-600 mt-2">
                      Source: {signal.source}
                    </p>
                  </div>

                  <span className="self-start sm:self-center px-3 py-1 rounded-lg bg-rose-950/50 border border-rose-900/60 text-rose-300 text-xs font-bold">
                    +{signal.points} pts
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Uncertainties */}
        {risk && risk.uncertainties.length > 0 && (
          <div className="bg-amber-950/20 border border-amber-800/60 rounded-2xl p-6 sm:p-8">
            <div className="flex items-center gap-2 mb-4">
              <TriangleAlert className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-bold text-white">
                Investigation Uncertainties
              </h2>
            </div>

            <div className="space-y-2">
              {risk.uncertainties.map((uncertainty, index) => (
                <div
                  key={`${uncertainty}-${index}`}
                  className="flex gap-2 text-xs text-amber-200/80"
                >
                  <span className="text-amber-400">•</span>
                  <span>{uncertainty}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evidence */}
        <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-blue-400" />
                Evidence Correlation
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Standardized forensic evidence emitted by the investigator
              </p>
            </div>

            <span className="text-xs px-2.5 py-1 rounded bg-blue-950 text-blue-300 border border-blue-800/50 font-mono">
              {evidence.length} Artifacts
            </span>
          </div>

          {evidence.length === 0 ? (
            <div className="border border-dashed border-gray-800 rounded-xl p-8 text-center bg-gray-900/30">
              <Cpu className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-gray-300 mb-1">
                No Evidence Artifacts
              </h4>
              <p className="text-xs text-gray-500">
                The investigation did not persist any evidence artifacts.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {evidence.map((item, index) => (
                <div
                  key={String(item.id || index)}
                  className="p-4 rounded-xl bg-gray-900/50 border border-gray-800"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-gray-200">
                          {String(item.category || 'General Evidence')}
                        </span>

                        <StatusBadge
                          status={String(item.status || 'UNKNOWN')}
                        />
                      </div>

                      <p className="text-xs text-gray-400 mt-2 leading-relaxed">
                        {String(item.description || 'No description provided.')}
                      </p>
                    </div>

                    <span className="text-[11px] text-gray-500 font-mono whitespace-nowrap">
                      {String(item.type || 'evidence')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Investigator Summary */}
        {investigation.result_summary && (
          <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-blue-400" />
              <h2 className="text-lg font-bold text-white">
                Investigator Summary
              </h2>
            </div>

            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
              {investigation.result_summary}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};