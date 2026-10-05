import React, { useEffect, useState } from 'react';
import { ArrowLeft, ShieldAlert, Cpu, RefreshCw, AlertCircle } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { Investigation } from '../types';
import { fetchInvestigationById } from '../api/investigations';

interface InvestigationPageProps {
  investigationId: string;
  initialData?: Investigation | null;
  onBack: () => void;
}

export const InvestigationPage: React.FC<InvestigationPageProps> = ({
  investigationId,
  initialData,
  onBack,
}) => {
  const [investigation, setInvestigation] = useState<Investigation | null>(initialData || null);
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

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back navigation */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-2 text-xs font-semibold text-gray-400 hover:text-white mb-6 transition cursor-pointer"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </button>

      {error ? (
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-800 text-rose-300">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-rose-400" />
            <div>
              <h3 className="font-bold text-white">Investigation Lookup Failed</h3>
              <p className="text-xs text-rose-300/80 mt-1">{error}</p>
            </div>
          </div>
          <button
            onClick={loadInvestigation}
            className="mt-4 px-4 py-2 bg-rose-900/60 hover:bg-rose-800 text-white rounded-lg text-xs font-semibold transition"
          >
            Retry Fetch
          </button>
        </div>
      ) : loading || !investigation ? (
        <div className="p-12 text-center bg-[#101726] border border-gray-800 rounded-2xl">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-400">Loading investigation record...</p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Header Card */}
          <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-black/40">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-800">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-xl sm:text-2xl font-bold text-white">
                    {investigation.title || 'Untitled Fraud Investigation'}
                  </h1>
                  <StatusBadge status={investigation.status} />
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
                  <span>ID:</span>
                  <span className="text-blue-400 select-all">{investigation.id}</span>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 font-mono">
                  v{investigation.vera_version}
                </span>
                <button
                  onClick={loadInvestigation}
                  className="p-2 rounded-lg bg-gray-900 border border-gray-800 hover:text-white transition cursor-pointer"
                  title="Refresh record"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            </div>

            {investigation.description && (
              <p className="text-sm text-gray-300 mt-4 leading-relaxed">
                {investigation.description}
              </p>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-800/80 text-xs">
              <div>
                <span className="text-gray-500 block mb-1">Status</span>
                <span className="font-semibold text-gray-200 capitalize">{investigation.status}</span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Created At</span>
                <span className="font-mono text-gray-300">
                  {new Date(investigation.created_at).toLocaleTimeString()}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Updated At</span>
                <span className="font-mono text-gray-300">
                  {new Date(investigation.updated_at).toLocaleTimeString()}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Engine</span>
                <span className="font-semibold text-blue-400">VERA Core</span>
              </div>
            </div>
          </div>

          {/* Placeholder Evidence Section */}
          <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-black/40">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-blue-400" />
                  Evidence Correlation & Forensic Graph
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Phase 01 Standardized Evidence Contract Placeholder
                </p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded bg-blue-950 text-blue-300 border border-blue-800/50 font-mono">
                0 Artifacts
              </span>
            </div>

            {/* Empty state / placeholder cards */}
            <div className="border border-dashed border-gray-800 rounded-xl p-8 text-center bg-gray-900/30">
              <Cpu className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-gray-300 mb-1">
                Evidence Engine Ready for Subsequent Phases
              </h4>
              <p className="text-xs text-gray-500 max-w-md mx-auto leading-relaxed">
                Future multi-modal analyzers (OCR extraction, Whisper STT, MesoNet deepfake verification, SEBI registry queries, and URL/APK classifiers) will emit standardized <code className="text-blue-400 font-mono">EvidenceContract</code> objects here.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
