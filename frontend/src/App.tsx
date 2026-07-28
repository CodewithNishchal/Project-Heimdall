import { useEffect, useMemo, useState } from 'react';
import { motion, Variants } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LeadTable from './components/LeadTable';
import ConfidenceGauge from './components/ConfidenceGauge';
import SignalAnalytics from './components/SignalAnalytics';
import TrendPanel from './components/TrendPanel';
import Settings from './components/Settings';
import SocialPostsView from './components/SocialPostsView';
import SignalDistribution from './components/SignalDistribution';
import { fetchLeads, fetchPipelineStatus } from './lib/api';
import type { LeadDetailResponse } from './types/lead';

export default function App() {
  const [leads, setLeads] = useState<LeadDetailResponse[]>([]);
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [isDark, setIsDark] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard');
  const [globalSearchTerm, setGlobalSearchTerm] = useState('');

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light-theme');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light-theme');
    }
  }, [isDark]);

  // Continuous backend health check & auto-reconnect polling
  useEffect(() => {
    let isMounted = true;

    const checkBackend = async () => {
      try {
        const apiLeads = await fetchLeads();
        if (isMounted) {
          setLeads(apiLeads);
          setStatus('success');
        }
      } catch (err) {
        if (isMounted) {
          setStatus('error');
        }
      }
    };

    // Initial fetch on mount
    checkBackend();

    // Polling interval:
    // Fast polling (3s) when offline to reconnect instantly as soon as backend starts.
    // Periodic health check (15s) when online to detect if server goes offline.
    const pollInterval = status === 'error' ? 3000 : 15000;
    const interval = setInterval(checkBackend, pollInterval);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [status]);

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

  const newTodayCount = useMemo(() => {
    const todayStr = new Date().toISOString().split('T')[0];
    return leads.filter((l) => {
      if (!l.last_updated) return l.badge === 'new_today';
      const leadDateStr = new Date(l.last_updated).toISOString().split('T')[0];
      return (l.badge === 'new_today' || leadDateStr === todayStr) && leadDateStr === todayStr;
    }).length;
  }, [leads]);

  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1,
      }
    }
  };

  const itemVariants: Variants = {
    hidden: { y: 20, opacity: 0, scale: 0.95 },
    show: { y: 0, opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 200, damping: 20 } }
  };

  return (
    <div className="relative flex flex-col h-screen bg-nexa-bg">
      {/* Golden Light Flare */}
      <div className="nexa-flare" />

      {/* ===== Main Dashboard Layout ===== */}
      <div className="relative z-10 flex flex-1 gap-2.5 sm:gap-4 px-4 py-3 lg:px-6 lg:py-4 overflow-hidden">
        {/* Left Column: Sidebar Navigation only */}
        <Sidebar
          currentView={currentView}
          setCurrentView={setCurrentView}
          isDark={isDark}
          setIsDark={setIsDark}
          status={status}
        />

        {/* Main Workspace */}
        <main className="flex min-w-0 flex-1 flex-col gap-4 pl-1 pr-3 py-1 overflow-y-auto overflow-x-hidden">
          {/* Top Header Bar */}
          <Header
            status={status}
            searchTerm={globalSearchTerm}
            setSearchTerm={setGlobalSearchTerm}
            isDark={isDark}
            setIsDark={setIsDark}
          />

          {currentView === 'settings' ? (
            <Settings />
          ) : currentView === 'social media posts' ? (
            <SocialPostsView />
          ) : currentView === 'pipeline' ? (
            <div className="flex flex-col flex-1 min-h-0">
              <LeadTable
                leads={leads}
                selectedLeadId={selectedLeadId}
                onSelectLead={setSelectedLeadId}
                onLeadIngested={(newLead) => setLeads([newLead, ...leads])}
                onLeadDeleted={(id) => {
                  if (selectedLeadId === id) setSelectedLeadId(null);
                  setLeads(leads.filter((l) => l.id !== id));
                }}
                status={status}
                externalSearchTerm={globalSearchTerm}
                isPipelineTab={true}
              />
            </div>
          ) : currentView === 'statistics' ? (
            <div className="flex flex-col flex-1 min-h-0">
              <LeadTable
                leads={leads.filter((l) => l.badge === 'new_today' || l.icp_fit === 'Strong')}
                selectedLeadId={selectedLeadId}
                onSelectLead={setSelectedLeadId}
                onLeadIngested={(newLead) => setLeads([newLead, ...leads])}
                onLeadDeleted={(id) => {
                  if (selectedLeadId === id) setSelectedLeadId(null);
                  setLeads(leads.filter((l) => l.id !== id));
                }}
                status={status}
                externalSearchTerm={globalSearchTerm}
                isTrackRecordsTab={true}
              />
            </div>
          ) : (
            <>
              {/* Default Main Dashboard Hero Banner */}
              <div className="flex items-center gap-3 px-1 pb-1">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#dfa32b] text-zinc-950 shadow-xs">
                  <Sparkles size={17} className="stroke-[2.5px]" />
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-zinc-100 tracking-tight">
                    Lead Intelligence Signals
                  </h2>
                  <p className="text-xs text-slate-600 dark:text-zinc-400 mt-0.5 font-medium">
                    Discover active intent signals and monitor target companies
                  </p>
                </div>
              </div>

              {/* ===== KPI Ribbon row ===== */}
              <motion.div
                className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 w-full flex-shrink-0"
                variants={containerVariants}
                initial="hidden"
                animate="show"
              >
                {/* Card 1: Total automated sweeps/scans processed */}
                <motion.div variants={itemVariants} className="nexa-card p-4 flex flex-col justify-between h-24 relative overflow-hidden">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                    Automated Sweeps
                  </span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-3xl font-extrabold text-zinc-100">
                      {totalScans}
                    </span>
                    <span className="text-xs text-emerald-400 font-mono">
                      ● Active checks
                    </span>
                  </div>
                </motion.div>

                {/* Card 2: Strong ICP matches found */}
                <motion.div variants={itemVariants} className="nexa-card p-4 flex flex-col justify-between h-24 relative overflow-hidden">
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
                </motion.div>

                {/* Card 3: NEW TODAY */}
                <motion.div variants={itemVariants} className="nexa-card p-4 flex flex-col justify-between h-24 relative overflow-hidden">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                    NEW TODAY
                  </span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-3xl font-extrabold text-zinc-100">
                      {newTodayCount}
                    </span>
                    <span className="text-xs text-zinc-500 font-mono">
                      Across 5 platforms
                    </span>
                  </div>
                </motion.div>

                {/* Card 4: Untapped pipeline revenue estimation */}
                <motion.div variants={itemVariants} className="nexa-card p-4 flex flex-col justify-between h-24 relative overflow-hidden">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                    Pipeline Value
                  </span>
                  <span className="text-3xl font-extrabold text-[var(--nexa-accent)] mt-1">
                    {pipelineRevenue}
                  </span>
                  <span className="text-xs text-zinc-500 font-mono">
                    Est. Contract value
                  </span>
                </motion.div>
              </motion.div>

              {/* Lead Intelligence Grid */}
              <motion.div
                className="flex flex-col flex-1 min-h-0"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.5 }}
              >
                <LeadTable
                  leads={leads}
                  selectedLeadId={selectedLeadId}
                  onSelectLead={setSelectedLeadId}
                  onLeadIngested={(newLead) => setLeads([newLead, ...leads])}
                  onLeadDeleted={(id) => {
                    if (selectedLeadId === id) setSelectedLeadId(null);
                    setLeads(leads.filter((l) => l.id !== id));
                  }}
                  status={status}
                  externalSearchTerm={globalSearchTerm}
                />
              </motion.div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
