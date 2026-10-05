import React from 'react';
import { ShieldAlert, Activity, Database, HardDrive, RefreshCw, Cpu } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { HealthResponse, ReadinessResponse } from '../types';

interface NavbarProps {
  health: HealthResponse | null;
  readiness: ReadinessResponse | null;
  loading: boolean;
  onRefresh: () => void;
  onNavigateHome: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  readiness,
  loading,
  onRefresh,
  onNavigateHome,
}) => {
  const dbStatus = readiness?.services?.database?.status || 'unavailable';
  const redisStatus = readiness?.services?.redis?.status || 'unavailable';
  const minioStatus = readiness?.services?.minio?.status || 'unavailable';

  return (
    <header className="border-b border-gray-800 bg-[#0c121e]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div
          className="flex items-center gap-3 cursor-pointer group"
          onClick={onNavigateHome}
        >
          <div className="p-2 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 group-hover:border-blue-400/50 transition">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-wider text-white">VERA</span>
              <span className="text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 font-semibold border border-blue-700/50">
                Phase 01
              </span>
            </div>
            <p className="text-xs text-gray-400 hidden sm:block">
              AI Investment Fraud Investigation Platform
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 bg-gray-900/90 border border-gray-800 rounded-lg px-3 py-1.5 text-xs">
            <div className="flex items-center gap-1.5 pr-2 border-r border-gray-800">
              <Activity className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-gray-400">API:</span>
              <StatusBadge status={health ? 'ready' : 'unavailable'} label={health ? 'Online' : 'Offline'} />
            </div>

            <div className="flex items-center gap-1.5 pr-2 border-r border-gray-800">
              <Database className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-gray-400">DB:</span>
              <StatusBadge status={dbStatus} label={dbStatus === 'ready' ? 'Ready' : 'Down'} />
            </div>

            <div className="flex items-center gap-1.5 pr-2 border-r border-gray-800">
              <Cpu className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-gray-400">Redis:</span>
              <StatusBadge status={redisStatus} label={redisStatus === 'ready' ? 'Ready' : 'Down'} />
            </div>

            <div className="flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-gray-400">Storage:</span>
              <StatusBadge status={minioStatus} label={minioStatus === 'ready' ? 'Ready' : 'Down'} />
            </div>
          </div>

          <button
            onClick={onRefresh}
            disabled={loading}
            title="Refresh system status"
            className="p-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-400 hover:text-white hover:border-gray-700 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
