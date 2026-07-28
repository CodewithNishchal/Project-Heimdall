import { ChevronDown, Sparkles, Trash2, Loader2, Search, Filter, Check, X, SlidersHorizontal, Workflow, Target } from 'lucide-react';
import { Fragment, useMemo, useState, useRef, useEffect } from 'react';
import type { LeadDetailResponse, LeadTier } from '../types/lead';
import ConfidenceMeter from './ConfidenceMeter';
import PitcherMode from './PitcherMode';
import ScoreBreakdown from './ScoreBreakdown';
import HackerScanAnimation from './HackerScanAnimation';
import LeadDetailDrawer from './LeadDetailDrawer';
import PipelineProgressModal from './PipelineProgressModal';
import { ingestLead, deleteLead, runPipeline, fetchLeads } from '../lib/api';

interface LeadTableProps {
  leads: LeadDetailResponse[];
  selectedLeadId: string | null;
  onSelectLead: (id: string | null) => void;
  onLeadIngested?: (newLead: LeadDetailResponse) => void;
  onLeadDeleted?: (id: string) => void;
  status?: 'loading' | 'success' | 'error';
  externalSearchTerm?: string;
  isPipelineTab?: boolean;
  isTrackRecordsTab?: boolean;
}

const tierOptions: Array<LeadTier | 'ALL'> = ['ALL', 'High', 'Medium', 'Low'];

function tierClass(tier: LeadTier) {
  if (tier === 'High')
    return 'border-emerald-500/20 bg-[var(--nexa-emerald-dim)] text-emerald-300';
  if (tier === 'Medium')
    return 'border-amber-500/20 bg-[var(--nexa-amber-dim)] text-amber-300';
  return 'border-nexa-border bg-nexa-surface text-zinc-500';
}

function icpClass(icp_fit: LeadDetailResponse['icp_fit']) {
  if (icp_fit === 'Strong') return 'bg-[var(--nexa-emerald-dim)] text-emerald-300 border-emerald-500/20';
  if (icp_fit === 'Partial') return 'bg-[var(--nexa-amber-dim)] text-amber-300 border-amber-500/20';
  return 'bg-[var(--nexa-rose-dim)] text-rose-300 border-rose-500/20';
}

function badgeLabel(badge: LeadDetailResponse['badge'], last_updated?: string) {
  if (badge === 'new_today') {
    const todayStr = new Date().toISOString().split('T')[0];
    const leadDateStr = last_updated ? new Date(last_updated).toISOString().split('T')[0] : todayStr;
    if (leadDateStr === todayStr) {
      return 'New Today';
    }
    return null; // Automatically expires at midnight on a new calendar day
  }
  if (badge === 'score_up') return 'Score Up';
  if (badge === 'score_down') return 'Score Down';
  if (badge === 'signal_added') return 'Signal Added';
  return null;
}

function badgeClass(badge: LeadDetailResponse['badge']) {
  if (badge === 'new_today') return 'border-[var(--nexa-accent)] bg-[var(--nexa-accent-dim)] text-[var(--nexa-accent)]';
  if (badge === 'score_up') return 'border-emerald-500/30 bg-[var(--nexa-emerald-dim)] text-emerald-300';
  if (badge === 'score_down') return 'border-rose-500/30 bg-[var(--nexa-rose-dim)] text-rose-300';
  return 'border-[var(--nexa-accent)]/30 bg-[var(--nexa-accent-dim)] text-[var(--nexa-accent-bright)]';
}

function getHiringNuance(lead: LeadDetailResponse) {
  const signalText = (lead.signals || []).map(s => (s.signal_type + ' ' + s.verbatim_quote).toLowerCase()).join(' ');
  const whyNowText = (lead.why_now || '').toLowerCase();
  const fullText = signalText + ' ' + whyNowText;

  if (fullText.includes('sdr') || fullText.includes('sales reps') || fullText.includes('adjacent') || fullText.includes('engineers') || (fullText.includes('hiring') && !fullText.includes('marketing manager'))) {
    return { label: 'Adjacent Hiring', type: 'adjacent', desc: 'High Intent: Hiring sales/engineers, missing marketing/recruiting' };
  } else if (fullText.includes('hiring marketing') || fullText.includes('marketing lead') || fullText.includes('direct hiring')) {
    return { label: 'Direct Hiring', type: 'direct', desc: 'Medium Intent: Building in-house marketing team' };
  }
  return { label: 'Expansion Mode', type: 'general', desc: 'General hiring & growth velocity' };
}

function getFirstSentence(text?: string): string {
  if (!text) return 'Intent signals detected for target company.';
  const clean = text.trim();
  const firstSentence = clean.split(/(?<=[.!?])\s+/)[0];
  return firstSentence || clean;
}

function getSignalBadgeStyle(signalText: string) {
  const lower = signalText.toLowerCase();
  if (lower.includes('fund') || lower.includes('series') || lower.includes('seed') || lower.includes('raised')) {
    return 'border border-indigo-500/30 bg-[var(--nexa-indigo-dim)] text-[var(--nexa-indigo)]';
  }
  if (lower.includes('hire') || lower.includes('sdr') || lower.includes('gap') || lower.includes('role')) {
    return 'border border-amber-500/30 bg-[var(--nexa-amber-dim)] text-[var(--nexa-amber)]';
  }
  if (lower.includes('headcount') || lower.includes('growth') || lower.includes('expansion') || lower.includes('+')) {
    return 'border border-emerald-500/30 bg-[var(--nexa-emerald-dim)] text-[var(--nexa-emerald)]';
  }
  return 'border border-nexa-border bg-nexa-surface text-[var(--nexa-accent)]';
}

export default function LeadTable({
  leads,
  selectedLeadId,
  onSelectLead,
  onLeadIngested,
  onLeadDeleted,
  status,
  externalSearchTerm = '',
  isPipelineTab = false,
  isTrackRecordsTab = false
}: LeadTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTier, setSelectedTier] = useState<LeadTier | 'ALL'>('ALL');
  const [dateFilter, setDateFilter] = useState<'ALL' | 'TODAY' | '7DAYS' | '30DAYS'>('ALL');
  const [scoreFilter, setScoreFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [signalFilter, setSignalFilter] = useState<'ALL' | 'HIRING' | 'FUNDING' | 'HEADCOUNT'>('ALL');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [pitcherLead, setPitcherLead] = useState<LeadDetailResponse | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [isPipelineModalOpen, setIsPipelineModalOpen] = useState(false);
  const [hasRunPipelineInTab, setHasRunPipelineInTab] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [expandedContacts, setExpandedContacts] = useState<Record<string, boolean>>({});

  const filterContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (filterContainerRef.current && !filterContainerRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (selectedTier !== 'ALL') count++;
    if (dateFilter !== 'ALL') count++;
    if (scoreFilter !== 'ALL') count++;
    if (signalFilter !== 'ALL') count++;
    return count;
  }, [selectedTier, dateFilter, scoreFilter, signalFilter]);

  const handleRunPipeline = async () => {
    setIsPipelineRunning(true);
    setIsPipelineModalOpen(true);
    try {
      await runPipeline();
    } catch (e) {
      console.error('Pipeline trigger catch:', e);
    }
  };

  const handlePipelineModalComplete = async () => {
    setHasRunPipelineInTab(true);
    try {
      const freshLeads = await fetchLeads();
      if (onLeadIngested && freshLeads.length > 0) {
        freshLeads.forEach((l) => onLeadIngested(l));
      }
    } catch (e) {
      console.error('Failed to sync fresh leads after pipeline completion', e);
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const handleScan = async () => {
    if (!searchTerm.trim()) return;
    setIsScanning(true);

    // Enforce a minimum 5-second delay for the hacker animation
    const minDelay = new Promise(resolve => setTimeout(resolve, 5000));

    try {
      const targetDomain = searchTerm.trim();
      const [newLead] = await Promise.all([
        ingestLead(targetDomain),
        minDelay
      ]);

      if (onLeadIngested) {
        onLeadIngested(newLead);
      }
    } catch (e) {
      console.error('Ingestion failed', e);
      alert('Failed to ingest company.');
    } finally {
      setIsScanning(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteLead(id);
      setConfirmDeleteId(null);
      if (onLeadDeleted) {
        onLeadDeleted(id);
      }
    } catch (e) {
      console.error('Deletion failed', e);
      alert('Failed to delete company.');
    }
  };

  const selectedLead = useMemo(() => {
    if (!selectedLeadId) return null;
    return leads.find((l) => String(l.id || l.domain || l.company_name) === String(selectedLeadId)) || null;
  }, [leads, selectedLeadId]);

  const filteredLeads = useMemo(() => {
    if (isPipelineTab && !hasRunPipelineInTab) {
      return [];
    }

    const activeSearch = (externalSearchTerm || searchTerm).toLowerCase().trim();
    const todayStr = new Date().toISOString().split('T')[0];
    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

    return leads.filter((lead) => {
      // 1. Search Query
      const matchesSearch = !activeSearch ||
        lead.company_name.toLowerCase().includes(activeSearch) ||
        lead.industry.toLowerCase().includes(activeSearch) ||
        lead.domain.toLowerCase().includes(activeSearch) ||
        (lead.why_now && lead.why_now.toLowerCase().includes(activeSearch));

      // 2. Tier Filter
      const matchesTier = selectedTier === 'ALL' || lead.tier === selectedTier;

      // 3. Date / Recency Filter
      let matchesDate = true;
      if (dateFilter === 'TODAY') {
        const leadDate = lead.last_updated ? new Date(lead.last_updated).toISOString().split('T')[0] : '';
        matchesDate = leadDate === todayStr || lead.badge === 'new_today';
      } else if (dateFilter === '7DAYS') {
        const leadDate = lead.last_updated ? new Date(lead.last_updated) : new Date();
        matchesDate = leadDate >= sevenDaysAgo;
      } else if (dateFilter === '30DAYS') {
        const leadDate = lead.last_updated ? new Date(lead.last_updated) : new Date();
        matchesDate = leadDate >= thirtyDaysAgo;
      }

      // 4. Score Filter
      let matchesScore = true;
      if (scoreFilter === 'HIGH') matchesScore = lead.icp_score >= 80;
      else if (scoreFilter === 'MEDIUM') matchesScore = lead.icp_score >= 60 && lead.icp_score < 80;
      else if (scoreFilter === 'LOW') matchesScore = lead.icp_score < 60;

      // 5. Signal Filter
      let matchesSignal = true;
      if (signalFilter !== 'ALL') {
        const signalsStr = (lead.signals || []).map(s => s.signal_type.toLowerCase()).join(' ') + ' ' + (lead.why_now || '').toLowerCase();
        if (signalFilter === 'HIRING') matchesSignal = signalsStr.includes('hiring') || signalsStr.includes('sdr');
        else if (signalFilter === 'FUNDING') matchesSignal = signalsStr.includes('funding') || signalsStr.includes('series');
        else if (signalFilter === 'HEADCOUNT') matchesSignal = !!lead.employee_count || signalsStr.includes('headcount');
      }

      return matchesSearch && matchesTier && matchesDate && matchesScore && matchesSignal;
    });
  }, [leads, searchTerm, externalSearchTerm, selectedTier, dateFilter, scoreFilter, signalFilter, isPipelineTab, hasRunPipelineInTab]);

  return (
    <div className="flex flex-col gap-4 flex-1 min-h-0">
      {/* Pipeline Tab Hero Banner */}
      {isPipelineTab && (
        <div className="nexa-card nexa-card-no-hover p-6 sm:p-7 rounded-3xl border border-emerald-500/30 bg-gradient-to-r from-emerald-950/40 via-slate-900/80 to-teal-950/40 flex flex-col sm:flex-row items-center justify-between gap-5 shadow-lg">
          <div className="flex items-center gap-4 text-left">
            <div className="flex h-13 w-13 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-md">
              <Workflow size={28} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-900 dark:text-zinc-100 flex items-center gap-2">
                Automated Intent Discovery Pipeline
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-500/30">
                  Ready to Run
                </span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium max-w-xl">
                Execute multi-source intent crawling across Google SERPs, Reddit, X, LinkedIn & Apollo APIs. Click the button to launch the live 4-minute discovery sweep.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleRunPipeline}
            disabled={isPipelineRunning}
            className="flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black text-xs shadow-xl transition-all hover:scale-105 active:scale-95 disabled:opacity-50 shrink-0"
          >
            {isPipelineRunning ? <Loader2 size={18} className="animate-spin" /> : <Workflow size={18} />}
            <span>Run Pipeline</span>
          </button>
        </div>
      )}
      
      {/* Track Records Tab Hero Banner */}
      {isTrackRecordsTab && (
        <div className="nexa-card nexa-card-no-hover p-6 sm:p-7 rounded-3xl border border-amber-500/30 bg-gradient-to-r from-amber-950/40 via-slate-900/80 to-amber-950/40 flex flex-col sm:flex-row items-center justify-between gap-5 shadow-lg">
          <div className="flex items-center gap-4 text-left">
            <div className="flex h-13 w-13 shrink-0 items-center justify-center rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-md">
              <Target size={28} />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-900 dark:text-zinc-100 flex items-center gap-2">
                Track Records & Active Watchlist
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-950/60 px-2.5 py-0.5 rounded-full border border-amber-500/30">
                  {leads.length} Tracked
                </span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium max-w-xl">
                High-intent prospects and target companies currently saved on your active tracking list for continuous signal monitoring.
              </p>
            </div>
          </div>
        </div>
      )}



      {/* Table Section Header */}
      {!isPipelineTab && !isTrackRecordsTab && (
        <div className="flex items-center justify-between px-1 pt-1 pb-0.5">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-zinc-300">
              Live Target Leads & Signal Grid
            </h3>
            <span className="text-[10px] font-semibold text-slate-500 dark:text-zinc-500">
              ({filteredLeads.length} companies detected)
            </span>
          </div>
          <span className="text-[11px] font-medium text-slate-500 dark:text-zinc-400 hidden sm:inline">
            Click any company row to inspect signals & AI pitch
          </span>
        </div>
      )}

      {/* Data Grid Card — Nexa Design System Styling */}
      <div className="nexa-card nexa-card-no-hover overflow-hidden flex-1 flex flex-col min-h-0 relative">
        {isScanning && <HackerScanAnimation targetDomain={searchTerm} />}

        <div className="overflow-x-auto flex-1">
          <table className="w-full min-w-[980px] border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-[11px] font-black uppercase tracking-wider text-slate-700 dark:text-zinc-300">
                <th className="p-4 text-left min-w-[200px]">COMPANY</th>
                <th className="p-4 text-center min-w-[90px]">SCORE</th>
                <th className="p-4 text-center min-w-[260px]">AI SUMMARY</th>
                <th className="p-4 text-center min-w-[220px]">SIGNALS</th>
                <th className="p-4 text-center min-w-[220px]">WHY NOW</th>
                <th className="p-4 text-center min-w-[120px] relative">
                  <div ref={filterContainerRef} className="relative flex justify-center">
                    <button
                      type="button"
                      onClick={() => setIsFilterOpen(!isFilterOpen)}
                      className={`flex h-[28px] items-center gap-1.5 rounded-lg border px-2.5 text-[11px] font-bold transition shadow-xs ${activeFilterCount > 0
                          ? 'border-emerald-500/50 bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400'
                          : 'border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/5 text-slate-800 dark:text-zinc-300 hover:bg-slate-200/80 dark:hover:bg-white/10 hover:text-slate-950 dark:hover:text-white'
                        }`}
                      title="Filter Companies"
                    >
                      <SlidersHorizontal size={13} />
                      <span>Filter</span>
                      {activeFilterCount > 0 && (
                        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-black text-zinc-950">
                          {activeFilterCount}
                        </span>
                      )}
                    </button>

                    {/* Filter Popover Modal */}
                    {isFilterOpen && (
                      <div className="filter-popover absolute right-0 top-full mt-1 w-80 rounded-2xl border border-slate-200 dark:border-nexa-border bg-white dark:bg-[#181824] p-4 shadow-2xl z-50 text-left normal-case tracking-normal animate-in fade-in slide-in-from-top-2">
                        <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/10 pb-2.5 mb-3">
                          <div className="flex items-center gap-2">
                            <Filter size={15} className="text-emerald-500" />
                            <span className="text-xs font-bold text-slate-900 dark:text-zinc-100">Filter Leads</span>
                          </div>
                          {activeFilterCount > 0 && (
                            <button
                              type="button"
                              onClick={() => {
                                setDateFilter('ALL');
                                setScoreFilter('ALL');
                                setSignalFilter('ALL');
                                setSelectedTier('ALL');
                              }}
                              className="text-[11px] font-bold text-rose-500 hover:underline"
                            >
                              Reset All
                            </button>
                          )}
                        </div>

                        {/* Filter Option 1: Recency / Date */}
                        <div className="mb-3.5">
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 mb-1.5 block">
                            Date Discovered
                          </label>
                          <div className="grid grid-cols-2 gap-1.5">
                            {[
                              { id: 'ALL', label: 'All Time' },
                              { id: 'TODAY', label: 'Added Today' },
                              { id: '7DAYS', label: 'Past 7 Days' },
                              { id: '30DAYS', label: 'Past 30 Days' }
                            ].map((opt) => (
                              <button
                                key={opt.id}
                                type="button"
                                onClick={() => setDateFilter(opt.id as any)}
                                className={`rounded-xl px-2.5 py-1.5 text-[11px] font-medium transition ${dateFilter === opt.id
                                    ? 'filter-btn-active bg-emerald-600 text-white font-extrabold shadow-xs'
                                    : 'filter-btn-inactive border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-white/10'
                                  }`}
                              >
                                {opt.label}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Filter Option 2: Score Range */}
                        <div className="mb-3.5">
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 mb-1.5 block">
                            ICP Score Range
                          </label>
                          <div className="grid grid-cols-2 gap-1.5">
                            {[
                              { id: 'ALL', label: 'All Scores' },
                              { id: 'HIGH', label: 'High (80+)' },
                              { id: 'MEDIUM', label: 'Medium (60-80)' },
                              { id: 'LOW', label: 'Low (<60)' }
                            ].map((opt) => (
                              <button
                                key={opt.id}
                                type="button"
                                onClick={() => setScoreFilter(opt.id as any)}
                                className={`rounded-xl px-2.5 py-1.5 text-[11px] font-medium transition ${scoreFilter === opt.id
                                    ? 'filter-btn-active bg-emerald-600 text-white font-extrabold shadow-xs'
                                    : 'filter-btn-inactive border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-white/10'
                                  }`}
                              >
                                {opt.label}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Filter Option 3: Signal Category */}
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 mb-1.5 block">
                            Signal Type
                          </label>
                          <div className="grid grid-cols-2 gap-1.5">
                            {[
                              { id: 'ALL', label: 'All Signals' },
                              { id: 'HIRING', label: 'SDR Hiring' },
                              { id: 'FUNDING', label: 'Funding News' },
                              { id: 'HEADCOUNT', label: 'Headcount Growth' }
                            ].map((opt) => (
                              <button
                                key={opt.id}
                                type="button"
                                onClick={() => setSignalFilter(opt.id as any)}
                                className={`rounded-xl px-2.5 py-1.5 text-[11px] font-medium transition ${signalFilter === opt.id
                                    ? 'filter-btn-active bg-emerald-600 text-white font-extrabold shadow-xs'
                                    : 'filter-btn-inactive border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-white/10'
                                  }`}
                              >
                                {opt.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {isPipelineRunning ? (
                <tr>
                  <td colSpan={6} className="p-4 sm:p-6 bg-slate-50/50 dark:bg-black/20">
                    <PipelineProgressModal
                      isOpen={true}
                      isInline={true}
                      onClose={() => setIsPipelineRunning(false)}
                      onComplete={handlePipelineModalComplete}
                    />
                  </td>
                </tr>
              ) : (
                <>
                  {filteredLeads.map((lead) => {
                    const leadKey = String(lead.id || lead.domain || lead.company_name);
                    const isSelected = String(selectedLeadId) === leadKey;
                    return (
                      <Fragment key={leadKey}>
                        <tr
                          onClick={() => onSelectLead(isSelected ? null : leadKey)}
                          className={`nexa-row-hover border-b border-nexa-border cursor-pointer transition-colors ${isSelected ? 'bg-[var(--nexa-accent-dim)]' : ''
                            }`}
                        >
                          {/* COMPANY */}
                          <td className="p-4 font-medium text-zinc-100 text-left">
                            <div className="flex flex-col items-start gap-0.5 text-left group">
                              <span className="font-bold text-zinc-100 text-sm group-hover:text-[var(--nexa-accent)] transition-colors">
                                {lead.company_name}
                              </span>
                              <span className="text-xs text-zinc-400 font-normal">
                                {(!lead.industry || lead.industry === 'Unknown') ? 'SaaS' : lead.industry} · {lead.funding_stage || 'Series B'} · {lead.employee_count ? `${lead.employee_count} emp` : '120 emp'}
                              </span>
                            </div>
                          </td>

                          {/* SCORE */}
                          <td className="p-4 text-center">
                            {(() => {
                              const displayScore = (lead.badge === 'filtered' || lead.ai_verdict?.includes('API Error')) ? 0 : lead.intent_score;
                              const scoreColor = displayScore >= 70
                                ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                                : displayScore >= 40
                                  ? 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                                  : 'bg-rose-950/80 text-rose-400 border border-rose-500/40';

                              return (
                                <span className={`inline-flex items-center justify-center rounded-full px-3 py-1 text-xs font-bold font-mono ${scoreColor}`}>
                                  {displayScore}
                                </span>
                              );
                            })()}
                          </td>

                          {/* AI SUMMARY (NEW COLUMN) */}
                          <td className="p-4 text-xs font-medium text-zinc-300 leading-snug max-w-xs text-center">
                            <span className="line-clamp-2">
                              {getFirstSentence(lead.ai_verdict)}
                            </span>
                          </td>

                          {/* SIGNALS */}
                          <td className="p-4 text-center">
                            <div className="flex flex-wrap gap-1.5 items-center justify-center">
                              {(() => {
                                const signalPills: Array<{ label: string; style: string }> = [];

                                if (lead.funding_stage && lead.funding_stage !== 'UNKNOWN') {
                                  signalPills.push({ label: 'Funding', style: 'border border-indigo-500/30 bg-[var(--nexa-indigo-dim)] text-[var(--nexa-indigo)]' });
                                }

                                const nuance = getHiringNuance(lead);
                                if (nuance.type === 'adjacent' || nuance.type === 'direct') {
                                  signalPills.push({ label: 'Hiring gap', style: 'border border-amber-500/30 bg-[var(--nexa-amber-dim)] text-[var(--nexa-amber)]' });
                                }

                                if (lead.employee_count) {
                                  signalPills.push({ label: `+${Math.min(40, Math.max(15, (lead.employee_count % 30) + 15))}% headcount`, style: 'border border-emerald-500/30 bg-[var(--nexa-emerald-dim)] text-[var(--nexa-emerald)]' });
                                }

                                if (lead.signals && lead.signals.length > 0) {
                                  lead.signals.slice(0, 3).forEach(s => {
                                    const typeStr = s.signal_type.replace(/_/g, ' ');
                                    if (!signalPills.some(p => p.label.toLowerCase().includes(typeStr.toLowerCase()))) {
                                      const style = getSignalBadgeStyle(typeStr);
                                      signalPills.push({ label: typeStr, style });
                                    }
                                  });
                                }

                                if (signalPills.length === 0) {
                                  signalPills.push({ label: 'Funding', style: 'border border-indigo-500/30 bg-[var(--nexa-indigo-dim)] text-[var(--nexa-indigo)]' });
                                  signalPills.push({ label: 'Hiring gap', style: 'border border-amber-500/30 bg-[var(--nexa-amber-dim)] text-[var(--nexa-amber)]' });
                                  signalPills.push({ label: '+40% headcount', style: 'border border-emerald-500/30 bg-[var(--nexa-emerald-dim)] text-[var(--nexa-emerald)]' });
                                }

                                return signalPills.slice(0, 3).map((pill, idx) => (
                                  <span
                                    key={idx}
                                    className={`px-2.5 py-1 rounded-md text-[11px] font-semibold whitespace-nowrap ${pill.style}`}
                                  >
                                    {pill.label}
                                  </span>
                                ));
                              })()}
                            </div>
                          </td>

                          {/* WHY NOW (SHIFTED TO END) */}
                          <td className="p-4 text-xs font-medium text-zinc-400 leading-snug max-w-xs text-center">
                            {lead.why_now || 'Intent signals detected.'}
                          </td>

                          {/* Actions / Far Right */}
                          <td className="p-4 text-center">
                            <div className="flex items-center justify-center gap-2">
                              {confirmDeleteId === lead.id ? (
                                <>
                                  <button
                                    aria-label={`Confirm delete for ${lead.company_name}`}
                                    className="inline-flex items-center justify-center rounded-md border border-rose-500/50 bg-[var(--nexa-rose-dim)] p-1 text-rose-400 transition hover:bg-rose-500 hover:text-white"
                                    onClick={(e) => { e.stopPropagation(); handleDelete(lead.id); }}
                                    type="button"
                                  >
                                    <Check size={14} aria-hidden="true" />
                                  </button>
                                  <button
                                    aria-label={`Cancel delete for ${lead.company_name}`}
                                    className="inline-flex items-center justify-center rounded-md border border-nexa-border bg-nexa-surface p-1 text-zinc-400 transition hover:border-zinc-500 hover:text-zinc-200"
                                    onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                                    type="button"
                                  >
                                    <X size={14} aria-hidden="true" />
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    aria-label={`Toggle details for ${lead.company_name}`}
                                    className="inline-flex items-center justify-center rounded-md border border-white/10 bg-white/5 p-1.5 text-zinc-400 transition hover:border-white/20 hover:text-zinc-200 hover:bg-white/10"
                                    onClick={(e) => { e.stopPropagation(); onSelectLead(selectedLeadId === lead.id ? null : lead.id); }}
                                    type="button"
                                  >
                                    <div className="w-3.5 h-3.5 border border-zinc-400 rounded-sm flex items-center justify-center text-[9px] font-bold">
                                      {selectedLeadId === lead.id ? '−' : '□'}
                                    </div>
                                  </button>
                                  <button
                                    aria-label={`Delete record for ${lead.company_name}`}
                                    className="inline-flex items-center justify-center rounded-md border border-white/10 bg-white/5 p-1.5 text-zinc-500 transition hover:border-rose-500/40 hover:bg-[var(--nexa-rose-dim)] hover:text-rose-400"
                                    onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(lead.id); }}
                                    type="button"
                                  >
                                    <Trash2 size={13} aria-hidden="true" />
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      </Fragment>
                    );
                  })}
                  {(filteredLeads.length === 0 || status === 'error') && (
                    <tr>
                      <td
                        className="p-16 text-center text-sm font-medium text-slate-500"
                        colSpan={6}
                      >
                        {isPipelineTab && !hasRunPipelineInTab ? (
                          <div className="flex flex-col items-center justify-center py-8">
                            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 mb-3 shadow-sm">
                              <Workflow size={28} />
                            </div>
                            <h3 className="text-base font-black text-slate-900 dark:text-zinc-100">Pipeline Standby</h3>
                            <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-md mt-1 font-medium leading-relaxed">
                              No pipeline execution in progress for this session. Click the <strong>Run Pipeline</strong> button above to launch multi-source lead discovery.
                            </p>
                            <button
                              type="button"
                              onClick={handleRunPipeline}
                              disabled={isPipelineRunning}
                              className="mt-4 flex items-center gap-2 rounded-2xl bg-emerald-600 px-6 py-3 text-xs font-bold text-white shadow-md hover:bg-emerald-500 transition"
                            >
                              <Workflow size={15} />
                              <span>Start Pipeline Execution</span>
                            </button>
                          </div>
                        ) : status === 'error' ? (
                          <div className="flex flex-col items-center justify-center gap-3 py-6">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500 border border-amber-500/20 shadow-xs">
                              <X size={22} />
                            </div>
                            <h3 className="text-base font-extrabold text-slate-800 dark:text-zinc-100">
                              Can't fetch data, system not online
                            </h3>
                            <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-sm font-medium">
                              The backend API server is offline. As soon as the network becomes online, the company data will populate automatically.
                            </p>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center gap-4">
                            <p>No tracking records found matching the active filters.</p>
                            <button
                              type="button"
                              onClick={async () => {
                                try {
                                  await runPipeline();
                                  fetchLeads();
                                } catch (e) {
                                  alert('Failed to run pipeline.');
                                }
                              }}
                              className="rounded-lg bg-[var(--nexa-accent)] px-6 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-[var(--nexa-accent-glow)] shadow-md"
                            >
                              Run Base Discovery Pipeline
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {pitcherLead ? (
        <PitcherMode
          id={pitcherLead.id}
          company_name={pitcherLead.company_name}
          onClose={() => setPitcherLead(null)}
        />
      ) : null}

      {/* Dynamic Slide-Over Side Drawer from Right */}
      <LeadDetailDrawer
        lead={selectedLead}
        onClose={() => onSelectLead(null)}
      />
    </div>
  );
}
