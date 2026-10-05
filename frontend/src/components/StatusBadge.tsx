import React from 'react';

interface StatusBadgeProps {
  status: 'ready' | 'ok' | 'created' | 'SUCCESS' | 'unavailable' | 'degraded' | 'FAILED' | 'PENDING' | string;
  label?: string;
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, pulse = false }) => {
  const normalized = status.toLowerCase();

  let colorClasses = 'bg-gray-800 text-gray-400 border-gray-700';
  let dotClasses = 'bg-gray-400';

  if (['ready', 'ok', 'success', 'created'].includes(normalized)) {
    colorClasses = 'bg-emerald-950/70 text-emerald-300 border-emerald-800/80';
    dotClasses = 'bg-emerald-400';
  } else if (['degraded', 'partial', 'pending'].includes(normalized)) {
    colorClasses = 'bg-amber-950/70 text-amber-300 border-amber-800/80';
    dotClasses = 'bg-amber-400';
  } else if (['unavailable', 'failed'].includes(normalized)) {
    colorClasses = 'bg-rose-950/70 text-rose-300 border-rose-800/80';
    dotClasses = 'bg-rose-400';
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClasses}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${dotClasses} ${pulse ? 'animate-ping' : ''}`}
      />
      {label || status}
    </span>
  );
};
