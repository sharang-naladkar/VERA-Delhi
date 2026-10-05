import React, { useState } from 'react';
import { ShieldCheck, ArrowRight, AlertTriangle, Upload, CheckCircle2, Server } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { HealthResponse, ReadinessResponse, Investigation } from '../types';
import { createInvestigation } from '../api/investigations';

interface HomePageProps {
  health: HealthResponse | null;
  readiness: ReadinessResponse | null;
  healthError: string | null;
  onOpenInvestigation: (investigation: Investigation) => void;
}

export const HomePage: React.FC<HomePageProps> = ({
  health,
  readiness,
  healthError,
  onOpenInvestigation,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleStartInvestigation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const result = await createInvestigation({
        title: title.trim() || 'Untitled Fraud Investigation',
        description: description.trim() || undefined,
        metadata: {
          submitted_from: 'web_frontend',
          phase: 'phase_01',
        },
      });
      onOpenInvestigation(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to initialize investigation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const dbStatus = readiness?.services?.database?.status || 'unavailable';
  const redisStatus = readiness?.services?.redis?.status || 'unavailable';
  const minioStatus = readiness?.services?.minio?.status || 'unavailable';

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Backend Unreachable Alert */}
      {healthError && (
        <div className="mb-8 p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-semibold text-rose-200">Backend Connection Warning</p>
            <p className="text-rose-300/80 mt-0.5">{healthError}</p>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/60 border border-blue-800/50 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-4">
          <ShieldCheck className="w-3.5 h-3.5" />
          Autonomous Forensic Intelligence
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-4">
          VERA
        </h1>
        <p className="text-lg text-gray-400 leading-relaxed">
          Autonomous AI-powered investment fraud investigation platform.
          Establishing multi-modal forensic contracts, modular analyzers, and fail-safe evidence pipelines.
        </p>
      </div>

      {/* Grid: Start Investigation + Infrastructure Probes */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
        {/* Main Action Form */}
        <div className="md:col-span-2 bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-black/40">
          <div className="flex items-center justify-between pb-6 border-b border-gray-800 mb-6">
            <div>
              <h2 className="text-lg font-bold text-white">Start New Investigation</h2>
              <p className="text-xs text-gray-400 mt-0.5">Initialize a new verified case session</p>
            </div>
            <StatusBadge status={health ? 'ready' : 'unavailable'} label={health ? 'API Online' : 'API Offline'} />
          </div>

          <form onSubmit={handleStartInvestigation} className="space-y-5">
            <div>
              <label htmlFor="title-input" className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5">
                Case Title / Target Subject
              </label>
              <input
                id="title-input"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Fake SEBI Guaranteed Trading Channel"
                className="w-full px-4 py-2.5 bg-gray-900/90 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label htmlFor="description-input" className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5">
                Preliminary Details / Suspicious Claims
              </label>
              <textarea
                id="description-input"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe suspected fraud, WhatsApp/Telegram groups, payment links, or advisor claims..."
                className="w-full px-4 py-2.5 bg-gray-900/90 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition resize-none"
              />
            </div>

            {/* Placeholder Evidence Upload Box */}
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5">
                Evidence Ingestion (Phase 01 Contract Placeholder)
              </label>
              <div className="border-2 border-dashed border-gray-800 rounded-xl p-5 text-center bg-gray-900/40">
                <Upload className="w-6 h-6 text-gray-500 mx-auto mb-2" />
                <p className="text-xs text-gray-400 font-medium">
                  Multi-modal evidence ingestion ready (Images, Screenshots, APKs, Audio, URLs)
                </p>
                <p className="text-[11px] text-gray-600 mt-1">
                  Full binary upload pipelines will be connected in subsequent phases.
                </p>
              </div>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-xs">
                {errorMessage}
              </div>
            )}

            <button
              id="start-investigation-btn"
              type="submit"
              disabled={isSubmitting || !health}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm shadow-lg shadow-blue-600/20 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <span>Initializing Case...</span>
              ) : (
                <>
                  <span>Start Investigation</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* System Subsystems & Health Details */}
        <div className="space-y-6">
          <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 shadow-xl shadow-black/40">
            <h3 className="text-sm font-bold uppercase tracking-wider text-gray-300 mb-4 flex items-center gap-2">
              <Server className="w-4 h-4 text-blue-400" />
              Subsystem Probes
            </h3>

            <div className="space-y-3.5">
              <div className="flex items-center justify-between p-3 rounded-lg bg-gray-900/70 border border-gray-800/80">
                <div>
                  <p className="text-xs font-semibold text-gray-200">PostgreSQL DB</p>
                  <p className="text-[11px] text-gray-500">
                    {readiness?.services?.database?.latency_ms
                      ? `${readiness.services.database.latency_ms}ms latency`
                      : 'Schema & migrations'}
                  </p>
                </div>
                <StatusBadge status={dbStatus} />
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-gray-900/70 border border-gray-800/80">
                <div>
                  <p className="text-xs font-semibold text-gray-200">Redis Cache</p>
                  <p className="text-[11px] text-gray-500">
                    {readiness?.services?.redis?.latency_ms
                      ? `${readiness.services.redis.latency_ms}ms latency`
                      : 'Job state & queue'}
                  </p>
                </div>
                <StatusBadge status={redisStatus} />
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-gray-900/70 border border-gray-800/80">
                <div>
                  <p className="text-xs font-semibold text-gray-200">MinIO Storage</p>
                  <p className="text-[11px] text-gray-500">
                    {readiness?.services?.minio?.latency_ms
                      ? `${readiness.services.minio.latency_ms}ms latency`
                      : 'Artifact bucket'}
                  </p>
                </div>
                <StatusBadge status={minioStatus} />
              </div>
            </div>
          </div>

          {/* Phase 01 Scope Card */}
          <div className="bg-blue-950/20 border border-blue-900/40 rounded-2xl p-5 text-xs text-gray-300">
            <div className="flex items-center gap-2 font-semibold text-blue-400 mb-2">
              <CheckCircle2 className="w-4 h-4" />
              Phase 01 Architecture
            </div>
            <p className="text-gray-400 leading-relaxed">
              Established replaceable provider interfaces, fail-safe status contracts, structured OpenAPI endpoints, and unified storage foundation.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
