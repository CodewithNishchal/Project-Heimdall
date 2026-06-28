import { useEffect, useMemo, useState } from 'react';
import { Bell, Shield, Sun, Moon, CheckCircle2 } from 'lucide-react';
import Sidebar from './components/Sidebar';
import LeadTable from './components/LeadTable';
import ConfidenceGauge from './components/ConfidenceGauge';
import SignalAnalytics from './components/SignalAnalytics';
import TrendPanel from './components/TrendPanel';
import Settings from './components/Settings';
import SignalDistribution from './components/SignalDistribution';
import { fetchLeads } from './lib/api';
import type { LeadDetailResponse } from './types/lead';

export default function App() {
  const [leads, setLeads] = useState<LeadDetailResponse[]>([]);
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [isDark, setIsDark] = useState(true);
  const [currentView, setCurrentView] = useState('dashboard');

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.remove('light-theme');
    } else {
      document.documentElement.classList.add('light-theme');
    }
  }, [isDark]);

  useEffect(() => {
    let isMounted = true;
    fetchLeads()
      .then((apiLeads) => {
        if (isMounted) {
          setLeads(apiLeads);
          setStatus('success');
        }
      })
      .catch(() => {
        if (isMounted) {
          setLeads([]);
          setStatus('error');
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  // Compute KPI values
  const totalScans = leads.length;
  
  const strongICPCount = useMemo(() => {
    return leads.filter((l) => l.icp_fit === 'Strong' || l.icp_fit === 'Partial').length;
  }, [leads]);

  const globalAvgConfidence = useMemo(() => {
    if (leads.length === 0) return 0;
    const sum = leads.reduce((acc, l) => acc + l.confidence.verified, 0);
    return Math.round(sum / leads.length);
  }, [leads]);

  const selectedLead = useMemo(() => {
    return leads.find((l) => l.id === selectedLeadId) || null;
  }, [leads, selectedLeadId]);

  const activeConfidence = selectedLead ? selectedLead.confidence.verified : globalAvgConfidence;

  const pipelineRevenue = useMemo(() => {
    const strong = leads.filter((l) => l.icp_fit === 'Strong').length;
    const partial = leads.filter((l) => l.icp_fit === 'Partial').length;
    const estimatedVal = (strong * 35000) + (partial * 12000);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(estimatedVal); 
  }, [leads]);

  return (
    <div className="relative flex flex-col h-screen bg-nexa-bg">
      {/* Golden Light Flare */}
      <div className="nexa-flare" />

      {/* ===== Top Header Bar ===== */}
      <div className="relative z-10 p-4 pb-1">
        <header className="nexa-card flex items-center justify-between px-5 py-3">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-600 to-amber-400 text-white shadow-[0_0_15px_rgba(232,164,58,0.4)]">
              <Shield size={20} strokeWidth={2.5} aria-hidden="true" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Heimdall
            </h1>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Connection Badge */}
            {status === 'loading' && (
              <span className="rounded-md border border-amber-600/30 bg-[var(--nexa-amber-dim)] px-2.5 py-1 font-mono text-[11px] text-amber-400">
                Connecting…
              </span>
            )}
            {status === 'success' && (
              <span className="rounded-md border border-emerald-500/30 bg-[var(--nexa-emerald-dim)] px-2.5 py-1 font-mono text-[11px] text-emerald-400 shadow-[0_0_8px_var(--nexa-emerald-dim)]">
                ● Engine Active
              </span>
            )}
            {status === 'error' && (
              <span className="rounded-md border border-rose-600/30 bg-[var(--nexa-rose-dim)] px-2.5 py-1 font-mono text-[11px] text-rose-400">
                ✕ Disconnected
              </span>
            )}
            
            {/* Bell Icon */}
            <button
              type="button"
              className="relative rounded-xl border border-white/5 bg-white/5 p-2.5 text-zinc-400 transition hover:bg-white/10 hover:text-zinc-200"
            >
              <div className="absolute right-2.5 top-2.5 h-1.5 w-1.5 rounded-full bg-[var(--nexa-accent)] shadow-[0_0_6px_var(--nexa-accent)]" />
              <Bell size={18} aria-hidden="true" />
            </button>
            
            {/* Theme Toggle */}
            <div className="flex items-center gap-1 rounded-xl border border-white/5 bg-white/5 p-1">
              <button
                type="button"
                className={`rounded-lg p-2 transition ${!isDark ? 'bg-[var(--nexa-accent)] text-zinc-900 shadow-[0_0_8px_var(--nexa-accent-glow)]' : 'text-zinc-400 hover:text-zinc-200'}`}
                onClick={() => setIsDark(false)}
              >
                <Sun size={16} aria-hidden="true" />
              </button>
              <button
                type="button"
                className={`rounded-lg p-2 transition ${isDark ? 'bg-[var(--nexa-accent)] text-zinc-900 shadow-[0_0_8px_var(--nexa-accent-glow)]' : 'text-zinc-400 hover:text-zinc-200'}`}
                onClick={() => setIsDark(true)}
              >
                <Moon size={16} aria-hidden="true" />
              </button>
            </div>
          </div>
        </header>
      </div>

      {/* ===== Main Dashboard Layout ===== */}
      <div className="relative z-10 flex flex-1 gap-6 p-10 pt-1 overflow-hidden">
        {/* Left Column: Sidebar Navigation only */}
        <div className="hidden w-52 flex-col gap-4 lg:flex self-start">
          <Sidebar currentView={currentView} setCurrentView={setCurrentView} />
        </div>

        {/* Main Workspace (Takes full width now) */}
        <main className="flex min-w-0 flex-1 flex-col gap-6 overflow-hidden">
          {currentView === 'settings' ? (
            <Settings />
          ) : (
            <>
              {/* ===== KPI Ribbon row ===== */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 w-full flex-shrink-0">
                {/* Card 1: Total automated sweeps/scans processed */}
                <div className="nexa-card p-4 flex flex-col justify-between h-24 relative overflow-hidden">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                    Automated Sweeps
                  </span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-3xl font-extrabold text-white">
                      {totalScans}
                    </span>
                    <span className="text-xs text-emerald-400 font-mono">
                      ● Active checks
                    </span>
                  </div>
                </div>

                {/* Card 2: Strong ICP matches found */}
                <div className="nexa-card p-4 flex flex-col justify-between h-24 relative overflow-hidden">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                    Strong & Partial Targets
                  </span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-3xl font-extrabold text-zinc-100">
                      {strongICPCount}
                    </span>
                    <span className="text-xs text-zinc-500 font-mono">
                      Match verified
                    </span>
                  </div>
                </div>

                {/* Card 3: AI Confidence Gauge Card (Interactive row selection) */}
                <div className="nexa-card p-2.5 px-4 flex items-center justify-between h-24 relative overflow-hidden">
                  <div className="flex flex-col justify-between h-full py-0.5 min-w-0 flex-1">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                      AI Confidence
                    </span>
                    <span className="text-xs text-zinc-400 font-mono">
                      {selectedLead ? 'Individual score' : 'Global average'}
                    </span>
                    <span className="text-xs font-semibold text-[var(--nexa-accent)] leading-tight truncate pr-2 mt-0.5" title={selectedLead ? selectedLead.company_name : 'Global Avg'}>
                      {selectedLead ? selectedLead.company_name : 'Global Avg'}
                    </span>
                  </div>
                  <div className="w-20 h-20 flex items-center justify-center flex-shrink-0">
                    <ConfidenceGauge verified={activeConfidence} total={100} noCard={true} />
                  </div>
                </div>

                {/* Card 4: Untapped pipeline revenue estimation */}
                <div className="nexa-card p-4 flex flex-col justify-between h-24 relative overflow-hidden">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                    Pipeline Value
                  </span>
                  <span className="text-3xl font-extrabold text-[var(--nexa-accent)] mt-1">
                    {pipelineRevenue}
                  </span>
                  <span className="text-xs text-zinc-500 font-mono">
                    Est. Contract value
                  </span>
                </div>
              </div>

              {/* Lead Intelligence Grid */}
              <LeadTable
                leads={leads}
                selectedLeadId={selectedLeadId}
                onSelectLead={setSelectedLeadId}
                onLeadIngested={(newLead) => setLeads([newLead, ...leads])}
                onLeadDeleted={(id) => {
                  if (selectedLeadId === id) setSelectedLeadId(null);
                  setLeads(leads.filter((l) => l.id !== id));
                }}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
}
