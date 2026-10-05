import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { HomePage } from './pages/HomePage';
import { InvestigationPage } from './pages/InvestigationPage';
import { useHealth } from './hooks/useHealth';
import { Investigation } from './types';

export const App: React.FC = () => {
  const { health, readiness, loading, error, refresh } = useHealth(8000);
  const [activeInvestigation, setActiveInvestigation] = useState<Investigation | null>(null);

  return (
    <div className="min-h-screen bg-[#090d16] text-gray-100 flex flex-col font-sans">
      <Navbar
        health={health}
        readiness={readiness}
        loading={loading}
        onRefresh={refresh}
        onNavigateHome={() => setActiveInvestigation(null)}
      />

      <main className="flex-1">
        {activeInvestigation ? (
          <InvestigationPage
            investigationId={activeInvestigation.id}
            initialData={activeInvestigation}
            onBack={() => setActiveInvestigation(null)}
          />
        ) : (
          <HomePage
            health={health}
            readiness={readiness}
            healthError={error}
            onOpenInvestigation={(inv) => setActiveInvestigation(inv)}
          />
        )}
      </main>

      <footer className="border-t border-gray-800/80 py-6 text-center text-xs text-gray-500 bg-[#0c121e]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>VERA — Phase 01 Foundation Architecture</span>
          <span>Fail-Safe Modular Forensic Investigation</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
