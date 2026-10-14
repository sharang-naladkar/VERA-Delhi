import React, { useState } from 'react';
import {
  ShieldCheck,
  ArrowRight,
  AlertTriangle,
  Upload,
  CheckCircle2,
  Server,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import {
  HealthResponse,
  ReadinessResponse,
  Investigation,
} from '../types';
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
  const [investigationText, setInvestigationText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleStartInvestigation = async (
    e: React.FormEvent<HTMLFormElement>,
  ) => {
    e.preventDefault();

    const submittedText = investigationText.trim();

    if (!submittedText) {
      setErrorMessage(
        'Please enter the suspicious message, claims, or other text you want VERA to investigate.',
      );
      return;
    }

    if (isSubmitting) {
      return;
    }

    if (!health) {
      setErrorMessage(
        'The backend is currently unavailable. Check the API connection and try again.',
      );
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const result = await createInvestigation({
        title: title.trim() || 'Untitled Fraud Investigation',
        description: description.trim() || undefined,
        text: submittedText,
        input_type: 'text',
        metadata: {
          submitted_from: 'web_frontend',
          phase: 'frontend_demo',
        },
      });

      onOpenInvestigation(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred while submitting the investigation.';

      setErrorMessage(
        `${message} Your entered information has been preserved. Check the connection before trying again.`,
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const dbStatus = readiness?.services?.database?.status || 'unavailable';
  const redisStatus = readiness?.services?.redis?.status || 'unavailable';
  const minioStatus = readiness?.services?.minio?.status || 'unavailable';

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Backend Connection Warning */}
      {healthError && (
        <div
          role="alert"
          className="mb-8 p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 flex items-start gap-3"
        >
          <AlertTriangle className="w-5 h-5 text-rose-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-semibold text-rose-200">
              Backend Connection Warning
            </p>
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
          AI-powered investment fraud investigation. Submit suspicious
          messages and claims for structured analysis, with findings
          presented according to the evidence returned by the backend.
        </p>
      </div>

      {/* Investigation Form and Infrastructure Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
        {/* Main Investigation Form */}
        <div className="md:col-span-2 bg-[#101726] border border-gray-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-black/40">
          <div className="flex items-center justify-between pb-6 border-b border-gray-800 mb-6 gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">
                Start New Investigation
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Submit suspicious content for analysis
              </p>
            </div>

            <StatusBadge
              status={health ? 'ready' : 'unavailable'}
              label={health ? 'API Online' : 'API Offline'}
            />
          </div>

          <form onSubmit={handleStartInvestigation} className="space-y-5">
            {/* Case Title */}
            <div>
              <label
                htmlFor="title-input"
                className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5"
              >
                Case Title / Target Subject
                <span className="normal-case tracking-normal text-gray-500">
                  {' '}
                  (Optional)
                </span>
              </label>

              <input
                id="title-input"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={255}
                placeholder="e.g. Suspicious investment advisory channel"
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-gray-900/90 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition disabled:opacity-60"
              />
            </div>

            {/* Investigation Text */}
            <div>
              <label
                htmlFor="investigation-text"
                className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5"
              >
                Suspicious Content to Investigate
                <span className="text-rose-400 ml-1">*</span>
              </label>

              <textarea
                id="investigation-text"
                rows={7}
                required
                value={investigationText}
                onChange={(e) => setInvestigationText(e.target.value)}
                placeholder={`Paste the suspicious message or claims here.

Example:
Our investment group guarantees 30% monthly returns with zero risk. Join our private trading channel today and register through this payment link...`}
                disabled={isSubmitting}
                aria-invalid={
                  Boolean(errorMessage) && !investigationText.trim()
                }
                aria-describedby="investigation-text-help"
                className="w-full px-4 py-3 bg-gray-900/90 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition resize-y disabled:opacity-60"
              />

              <div className="flex items-start justify-between gap-3 mt-2">
                <p
                  id="investigation-text-help"
                  className="text-xs text-gray-500 leading-relaxed"
                >
                  Required. Provide the original text or message you want
                  VERA to analyze. Include URLs or claims as text when relevant.
                </p>

                <span className="text-xs text-gray-500 whitespace-nowrap">
                  {investigationText.length} characters
                </span>
              </div>
            </div>

            {/* Preliminary Details */}
            <div>
              <label
                htmlFor="description-input"
                className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5"
              >
                Additional Case Details
                <span className="normal-case tracking-normal text-gray-500">
                  {' '}
                  (Optional)
                </span>
              </label>

              <textarea
                id="description-input"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add context, where the message was received, or other relevant details..."
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-gray-900/90 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition resize-y disabled:opacity-60"
              />
            </div>

            {/* Evidence Upload Status */}
            <div>
              <p className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5">
                Additional Evidence
              </p>

              <div className="border border-dashed border-gray-700 rounded-xl p-5 bg-gray-900/40">
                <div className="flex items-start gap-3">
                  <Upload className="w-6 h-6 text-gray-500 flex-shrink-0" />

                  <div>
                    <p className="text-sm text-gray-300 font-medium">
                      File uploads are not available in this form
                    </p>

                    <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                      Image, audio, video, and APK upload workflows are not
                      connected here. Submit text for analysis, and do not
                      assume that additional files have been uploaded or
                      examined.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Submission Error */}
            {errorMessage && (
              <div
                role="alert"
                className="p-4 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-sm"
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />

                  <div>
                    <p className="font-semibold mb-1">
                      Investigation could not be submitted
                    </p>
                    <p className="leading-relaxed">{errorMessage}</p>
                  </div>
                </div>
              </div>
            )}

            {/* API Availability Notice */}
            {!health && (
              <p className="text-xs text-amber-300/90 leading-relaxed">
                The investigation service is unavailable. Your entered
                information will remain in the form while you check the
                backend connection.
              </p>
            )}

            {/* Submit */}
            <button
              id="start-investigation-btn"
              type="submit"
              disabled={isSubmitting || !health}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm shadow-lg shadow-blue-600/20 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <span
                    className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"
                    aria-hidden="true"
                  />
                  <span>Submitting Investigation...</span>
                </>
              ) : (
                <>
                  <span>Start Investigation</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <p className="text-center text-xs text-gray-500">
              Analysis results depend on the evidence and capabilities
              available to the backend.
            </p>
          </form>
        </div>

        {/* Infrastructure Status */}
        <div className="space-y-6">
          <div className="bg-[#101726] border border-gray-800 rounded-2xl p-6 shadow-xl shadow-black/40">
            <h3 className="text-sm font-bold uppercase tracking-wider text-gray-300 mb-4 flex items-center gap-2">
              <Server className="w-4 h-4 text-blue-400" />
              Subsystem Probes
            </h3>

            <div className="space-y-3.5">
              {/* PostgreSQL */}
              <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-gray-900/70 border border-gray-800/80">
                <div>
                  <p className="text-xs font-semibold text-gray-200">
                    PostgreSQL DB
                  </p>

                  <p className="text-[11px] text-gray-500">
                    {readiness?.services?.database?.latency_ms != null
                      ? `${readiness.services.database.latency_ms}ms latency`
                      : 'Database readiness'}
                  </p>
                </div>

                <StatusBadge status={dbStatus} />
              </div>

              {/* Redis */}
              <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-gray-900/70 border border-gray-800/80">
                <div>
                  <p className="text-xs font-semibold text-gray-200">
                    Redis Cache
                  </p>

                  <p className="text-[11px] text-gray-500">
                    {readiness?.services?.redis?.latency_ms != null
                      ? `${readiness.services.redis.latency_ms}ms latency`
                      : 'Cache readiness'}
                  </p>
                </div>

                <StatusBadge status={redisStatus} />
              </div>

              {/* MinIO */}
              <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-gray-900/70 border border-gray-800/80">
                <div>
                  <p className="text-xs font-semibold text-gray-200">
                    MinIO Storage
                  </p>

                  <p className="text-[11px] text-gray-500">
                    {readiness?.services?.minio?.latency_ms != null
                      ? `${readiness.services.minio.latency_ms}ms latency`
                      : 'Storage readiness'}
                  </p>
                </div>

                <StatusBadge status={minioStatus} />
              </div>
            </div>
          </div>

          {/* Architecture Information */}
          <div className="bg-blue-950/20 border border-blue-900/40 rounded-2xl p-5 text-xs text-gray-300">
            <div className="flex items-center gap-2 font-semibold text-blue-400 mb-2">
              <CheckCircle2 className="w-4 h-4" />
              Investigation Workflow
            </div>

            <p className="text-gray-400 leading-relaxed">
              Submit suspicious text to the investigation API. VERA will
              return the investigation status and whatever findings are
              available. Missing or unavailable analysis is not treated
              as proof that the content is safe.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};