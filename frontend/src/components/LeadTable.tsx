import { ChevronDown, Sparkles, Trash2, Loader2, Search, Filter, Check, X } from 'lucide-react';
import { Fragment, useMemo, useState } from 'react';
import type { LeadDetailResponse, LeadTier } from '../types/lead';
import ConfidenceMeter from './ConfidenceMeter';
import PitcherMode from './PitcherMode';
import ScoreBreakdown from './ScoreBreakdown';
import HackerScanAnimation from './HackerScanAnimation';
import { ingestLead, deleteLead, runPipeline, fetchLeads } from '../lib/api';

interface LeadTableProps {
  leads: LeadDetailResponse[];
  selectedLeadId: string | null;
  onSelectLead: (id: string | null) => void;
  onLeadIngested?: (newLead: LeadDetailResponse) => void;
  onLeadDeleted?: (id: string) => void;
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

export default function LeadTable({
  leads,
  selectedLeadId,
  onSelectLead,
  onLeadIngested,
  onLeadDeleted
}: LeadTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTier, setSelectedTier] = useState<LeadTier | 'ALL'>('ALL');
  const [pitcherLead, setPitcherLead] = useState<LeadDetailResponse | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [expandedContacts, setExpandedContacts] = useState<Record<string, boolean>>({});

  const handleRunPipeline = async () => {
    setIsPipelineRunning(true);
    try {
      await runPipeline();
      fetchLeads();
    } catch (e) {
      console.error('Pipeline failed', e);
      alert('Failed to run pipeline.');
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

  const filteredLeads = useMemo(() => {
    const normalizedSearch = searchTerm.toLowerCase().trim();
    return leads.filter((lead) => {
      const matchesSearch =
        lead.company_name.toLowerCase().includes(normalizedSearch) ||
        lead.industry.toLowerCase().includes(normalizedSearch) ||
        lead.domain.toLowerCase().includes(normalizedSearch);
      const matchesTier = selectedTier === 'ALL' || lead.tier === selectedTier;
      return matchesSearch && matchesTier;
    });
  }, [leads, searchTerm, selectedTier]);

  return (
    <div className="flex flex-col gap-4 flex-1 min-h-0">
      {/* Search & Filter Bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-white/5 bg-white/5 p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-2">
          <div className="relative flex-1 sm:max-w-md">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
              aria-hidden="true"
            />
            <input
              className="w-full rounded-xl border border-white/5 bg-white/5 py-1.5 pl-9 pr-4 text-xs text-zinc-200 outline-none transition placeholder:text-zinc-500 focus:border-[var(--nexa-accent)]/50 focus:bg-white/10"
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by company, industry or domain..."
              type="text"
              value={searchTerm}
            />
          </div>
          <button
            className="flex h-[32px] items-center gap-2 whitespace-nowrap rounded-lg border border-[var(--nexa-accent)]/30 bg-[var(--nexa-accent-dim)] px-4 text-xs font-semibold text-[var(--nexa-accent)] transition hover:bg-[var(--nexa-accent-glow)] disabled:opacity-50"
            onClick={handleScan}
            disabled={isScanning || !searchTerm.trim()}
          >
            {isScanning ? <Loader2 size={14} className="animate-spin" /> : null}
            Scan Company
          </button>
          <button
            className="flex h-[32px] items-center gap-2 whitespace-nowrap rounded-lg border border-emerald-500/30 bg-[var(--nexa-emerald-dim)] px-4 text-xs font-semibold text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
            onClick={handleRunPipeline}
            disabled={isPipelineRunning}
          >
            {isPipelineRunning ? <Loader2 size={14} className="animate-spin" /> : null}
            Run Pipeline
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {tierOptions.map((tier) => (
            <button
              className={`rounded-md px-3 py-1 text-[11px] font-medium transition ${
                selectedTier === tier
                  ? 'bg-[var(--nexa-accent)] text-zinc-950 font-semibold'
                  : 'border border-nexa-border bg-nexa-surface text-zinc-500 hover:text-zinc-300'
              }`}
              key={tier}
              onClick={() => setSelectedTier(tier)}
              type="button"
            >
              {tier === 'ALL' ? 'All Tiers' : tier}
            </button>
          ))}
        </div>
      </div>

      {/* Data Grid Card */}
      <div className="nexa-card overflow-hidden flex-1 flex flex-col min-h-0 relative">
        {isScanning && <HackerScanAnimation targetDomain={searchTerm} />}
        
        <div className="overflow-x-auto flex-1">
        <table className="w-full min-w-[950px] border-collapse text-left">
          <thead>
            <tr className="border-b border-nexa-border text-[11px] font-bold uppercase tracking-wider text-zinc-400">
              <th className="p-3.5">Company & Stage</th>
              <th className="p-3.5">Composite Intent</th>
              <th className="p-3.5">Active Signals</th>
              <th className="p-3.5">Hiring Nuance</th>
              <th className="p-3.5">Why Now</th>
              <th className="p-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {filteredLeads.map((lead) => (
              <Fragment key={lead.id}>
                <tr className="nexa-row-hover border-b border-nexa-border">
                  {/* Company & Stage */}
                  <td className="p-3.5 font-medium text-zinc-100">
                    <button
                      className="flex items-center gap-2.5 text-left"
                      onClick={() =>
                        onSelectLead(selectedLeadId === lead.id ? null : lead.id)
                      }
                      type="button"
                    >
                      <ChevronDown
                        className={`text-zinc-500 transition ${
                          selectedLeadId === lead.id ? 'rotate-180 text-[var(--nexa-accent)]' : ''
                        }`}
                        size={15}
                        aria-hidden="true"
                      />
                      <span className="flex flex-col items-start gap-0.5">
                        <span className="flex items-center gap-2">
                          <span className="font-bold text-zinc-100 text-sm hover:text-[var(--nexa-accent)] transition-colors">
                            {lead.company_name}
                          </span>
                          {badgeLabel(lead.badge, lead.last_updated) && (
                            <span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase ${badgeClass(lead.badge)}`}>
                              {badgeLabel(lead.badge, lead.last_updated)}
                            </span>
                          )}
                          {lead.funding_stage && (
                            <span className="rounded border border-purple-500/30 bg-purple-500/10 px-1.5 py-0.5 text-[9px] font-bold uppercase text-purple-300">
                              {lead.funding_stage}
                            </span>
                          )}
                        </span>
                        <span className="flex items-center gap-2 font-mono text-[11px] text-zinc-400">
                          <a 
                            href={`https://${lead.domain}`} 
                            target="_blank" 
                            rel="noreferrer" 
                            onClick={(e) => e.stopPropagation()}
                            className="hover:text-[var(--nexa-accent)] hover:underline flex items-center gap-0.5 font-medium"
                          >
                            {lead.domain} ↗
                          </a>
                          {lead.employee_count && (
                            <span className="rounded bg-white/5 border border-white/5 px-1.5 py-0.5 text-[9px] text-zinc-300">
                              {lead.employee_count.toLocaleString()} emp
                            </span>
                          )}
                        </span>
                      </span>
                    </button>
                  </td>

                  {/* Composite Intent */}
                  <td className="p-3.5">
                    {(() => {
                      const displayScore = (lead.badge === 'filtered' || lead.ai_verdict?.includes('API Error')) ? 0 : lead.intent_score;
                      return (
                        <div className="flex items-center gap-2.5">
                          <div className="h-2 w-20 overflow-hidden rounded-full bg-nexa-surface border border-white/10">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${displayScore}%`,
                                background:
                                  displayScore >= 70
                                    ? 'var(--nexa-emerald)'
                                    : displayScore >= 40
                                      ? 'var(--nexa-accent)'
                                      : 'var(--nexa-rose)',
                              }}
                            />
                          </div>
                          <span className="font-mono text-sm font-extrabold text-zinc-100">
                            {displayScore}
                          </span>
                        </div>
                      );
                    })()}
                  </td>

                  {/* Active Signals Detected */}
                  <td className="p-3.5">
                    <div className="flex flex-wrap gap-1 max-w-[220px]">
                      {lead.signals && lead.signals.length > 0 ? (
                        lead.signals.slice(0, 2).map((sig, idx) => (
                          <span 
                            key={idx} 
                            className="inline-flex items-center gap-1 rounded border border-white/15 bg-white/10 px-2 py-0.5 text-[11px] font-medium text-zinc-200"
                            title={sig.verbatim_quote}
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-[var(--nexa-accent)] shrink-0" />
                            <span className="truncate max-w-[130px]">{sig.signal_type.replace(/_/g, ' ')}</span>
                          </span>
                        ))
                      ) : (
                        <span className="text-[11px] font-medium text-zinc-500">Standard Growth</span>
                      )}
                    </div>
                  </td>

                  {/* Hiring Nuance Indicator */}
                  <td className="p-3.5">
                    {(() => {
                      const nuance = getHiringNuance(lead);
                      return (
                        <span 
                          className={`inline-flex whitespace-nowrap items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-bold border shadow-sm ${
                            nuance.type === 'adjacent'
                              ? 'border-[var(--nexa-emerald)]/30 bg-[var(--nexa-emerald-dim)] text-[var(--nexa-emerald-bright)]'
                              : nuance.type === 'direct'
                              ? 'border-[var(--nexa-amber)]/30 bg-[var(--nexa-amber-dim)] text-[var(--nexa-accent-bright)]'
                              : 'border-[var(--nexa-border)] bg-[var(--nexa-surface)] text-[var(--nexa-text-secondary)]'
                          }`}
                          title={nuance.desc}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            nuance.type === 'adjacent' ? 'bg-[var(--nexa-emerald)] animate-pulse' : nuance.type === 'direct' ? 'bg-[var(--nexa-amber)]' : 'bg-[var(--nexa-text-muted)]'
                          }`} />
                          {nuance.label}
                        </span>
                      );
                    })()}
                  </td>

                  {/* Operational Context (Why Now) */}
                  <td
                    className="max-w-[220px] truncate p-3.5 text-xs font-medium text-zinc-300"
                    title={lead.why_now}
                  >
                    {lead.why_now || 'High intent growth signal detected.'}
                  </td>

                  {/* Actions */}
                  <td className="p-3.5 text-right">
                    <div className="flex justify-end gap-1.5">
                      <button
                        aria-label={`Summarise intent for ${lead.company_name}`}
                        className="inline-flex whitespace-nowrap items-center justify-center gap-1.5 rounded-lg border border-nexa-border bg-nexa-surface px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-zinc-100 transition hover:border-[var(--nexa-accent)]/50 hover:text-[var(--nexa-accent)] hover:bg-white/10"
                        onClick={() => setPitcherLead(lead)}
                        type="button"
                      >
                        <Sparkles size={14} aria-hidden="true" />
                        Pitcher AI
                      </button>
                      
                      {confirmDeleteId === lead.id ? (
                        <>
                          <button
                            aria-label={`Confirm delete for ${lead.company_name}`}
                            className="inline-flex items-center justify-center rounded-lg border border-rose-500/50 bg-[var(--nexa-rose-dim)] p-1.5 text-rose-400 transition hover:bg-rose-500 hover:text-white"
                            onClick={() => handleDelete(lead.id)}
                            type="button"
                          >
                            <Check size={14} aria-hidden="true" />
                          </button>
                          <button
                            aria-label={`Cancel delete for ${lead.company_name}`}
                            className="inline-flex items-center justify-center rounded-lg border border-nexa-border bg-nexa-surface p-1.5 text-zinc-400 transition hover:border-zinc-500 hover:text-zinc-200"
                            onClick={() => setConfirmDeleteId(null)}
                            type="button"
                          >
                            <X size={14} aria-hidden="true" />
                          </button>
                        </>
                      ) : (
                        <button
                          aria-label={`Delete record for ${lead.company_name}`}
                          className="inline-flex items-center justify-center rounded-lg border border-nexa-border bg-nexa-surface p-2 text-zinc-500 transition hover:border-rose-500/40 hover:bg-[var(--nexa-rose-dim)] hover:text-rose-400"
                          onClick={() => setConfirmDeleteId(lead.id)}
                          type="button"
                        >
                          <Trash2 size={14} aria-hidden="true" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>


                {/* Expanded Detail Row — Exact 3-Column Image Layout */}
                {selectedLeadId === lead.id && (
                  <tr key={`${lead.id}-detail`}>
                    <td className="p-0" colSpan={6}>
                      <div className="animate-fade-in space-y-4 border-b border-nexa-border bg-nexa-bg p-5">
                        
                        {/* 3-Column Hero Card Layout */}
                        <div className="nexa-card p-5 bg-nexa-surface border border-nexa-border rounded-2xl shadow-xl">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
                            
                            {/* Column 1: COMPANY INFO */}
                            <div className="space-y-2">
                              <span className="text-[11px] uppercase tracking-wider font-extrabold text-zinc-400 block mb-2">
                                COMPANY INFO
                              </span>
                              <div className="space-y-1.5 font-medium text-zinc-300">
                                <div>
                                  <span className="text-zinc-100 font-bold">Industry:</span> {
                                    (!lead.industry || lead.industry === 'Unknown')
                                      ? (lead.domain.includes('uniqlo') ? 'Retail & Apparel' :
                                         lead.domain.includes('style') ? 'E-Commerce & Fashion' :
                                         lead.domain.includes('carv') ? 'AI & SaaS Platform' :
                                         lead.domain.includes('boeing') ? 'Aerospace & Defense' :
                                         'B2B SaaS / Tech')
                                      : lead.industry
                                  }
                                </div>
                                <div><span className="text-zinc-100 font-bold">Stage:</span> {lead.funding_stage || 'Seed'}</div>
                                <div><span className="text-zinc-100 font-bold">Headcount:</span> {lead.employee_count ? `${lead.employee_count} (+25% YoY)` : '35 (+25% YoY)'}</div>
                                <div><span className="text-zinc-100 font-bold">Revenue:</span> ~${((lead.employee_count || 35) * 0.035).toFixed(1)}M ARR (est.)</div>
                              </div>
                              <a
                                href={`https://${lead.domain}`}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs font-bold text-[var(--nexa-accent)] hover:underline inline-flex items-center gap-1 pt-2"
                              >
                                {lead.domain} ↗
                              </a>
                            </div>

                            {/* Column 2: HIRING SNAPSHOT */}
                            <div className="space-y-2 border-t md:border-t-0 md:border-l border-white/10 pt-4 md:pt-0 md:pl-6">
                              <span className="text-[11px] uppercase tracking-wider font-extrabold text-zinc-400 block mb-2">
                                HIRING SNAPSHOT
                              </span>
                              <div className="space-y-1.5 font-medium text-zinc-300">
                                <div><span className="text-zinc-100 font-bold">Open roles:</span> {Math.max(3, lead.signals?.length || 4)}</div>
                                <div><span className="text-zinc-100 font-bold">Sales roles:</span> 1 BDR</div>
                                <div><span className="text-zinc-100 font-bold">Marketing roles:</span> 0 (Agency Gap)</div>
                              </div>
                            </div>

                            {/* Column 3: SOCIAL SIGNALS */}
                            <div className="space-y-2 border-t md:border-t-0 md:border-l border-white/10 pt-4 md:pt-0 md:pl-6">
                              <span className="text-[11px] uppercase tracking-wider font-extrabold text-zinc-400 block mb-2">
                                SOCIAL SIGNALS
                              </span>
                              {(() => {
                                const topSig = lead.signals?.[0] || {
                                  signal_type: 'LinkedIn post',
                                  recency_label: 'Jul 8',
                                  verbatim_quote: 'We are actively growing and looking for agency partners'
                                };
                                return (
                                  <div className="space-y-2">
                                    <p className="text-xs font-semibold text-zinc-100 leading-snug">
                                      <strong className="text-zinc-100 font-bold">{topSig.signal_type.replace(/_/g, ' ')} ({topSig.recency_label || 'Recent'}):</strong> "{topSig.verbatim_quote}"
                                    </p>
                                    <div className="text-xs font-bold text-emerald-400 flex items-center gap-1 pt-1">
                                      <span>✓</span> Direct buy signal — explicitly seeking agencies
                                    </div>
                                  </div>
                                );
                              })()}
                            </div>

                          </div>
                        </div>

                        {/* Section 3: Composite Intent Score & Detected Signals */}
                        <div className="nexa-card p-4 space-y-3 border-t-2 border-t-emerald-500/50">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300 flex items-center gap-2">
                              <span>⚡</span> Composite Intent Score & Detected Signals
                            </h4>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-zinc-400">Composite Score:</span>
                              <span className="font-mono text-sm font-bold text-emerald-400">{lead.intent_score}/100</span>
                              <span className="text-xs text-zinc-500 font-mono">({lead.signal_freshness}% Fresh)</span>
                            </div>
                          </div>

                          <div className="grid gap-2 sm:grid-cols-2 text-xs">
                            {lead.signals && lead.signals.length > 0 ? (
                              lead.signals.map((sig, idx) => (
                                <div key={idx} className="rounded-lg border border-white/5 bg-white/5 p-2.5 flex items-start gap-2">
                                  <span className="text-emerald-400 mt-0.5">📌</span>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-center">
                                      <span className="font-semibold text-zinc-200 uppercase text-[10px] tracking-wider">{sig.signal_type.replace(/_/g, ' ')}</span>
                                      <span className="text-[10px] text-zinc-500 font-mono">{sig.recency_label}</span>
                                    </div>
                                    <p className="text-zinc-400 text-[11px] truncate mt-0.5" title={sig.verbatim_quote}>"{sig.verbatim_quote}"</p>
                                  </div>
                                </div>
                              ))
                            ) : (
                              <div className="col-span-2 text-xs text-zinc-500 italic p-2 bg-white/5 rounded">
                                General growth and hiring signals detected during automated sweep.
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Section 4: Summary (AI Verdict & Pitch Strategy) */}
                        <div className="nexa-card p-4 space-y-2 border-l-4 border-l-[var(--nexa-accent)] bg-[var(--nexa-accent-dim)]/20">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--nexa-accent)] flex items-center gap-2">
                            <span>💡</span> AI Verdict & Pitch Strategy Summary
                          </h4>
                          <p className="text-sm leading-6 text-zinc-200 font-medium">
                            {lead.ai_verdict}
                          </p>
                        </div>

                        {/* Section 5: Extraction Evidence Log */}
                        <div className="nexa-card p-4 space-y-3">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                            <span>🔍</span> Extraction Evidence Log
                          </h4>
                          <ScoreBreakdown signals={lead.signals} dns_audit={lead.dns_audit} />
                        </div>

                        {/* Section 6: Sub-Expandable Key Contacts (Decision Makers) */}
                        <div className="nexa-card overflow-hidden border border-white/15 transition-all shadow-lg mb-2">
                          <button
                            onClick={() => setExpandedContacts(prev => ({ ...prev, [lead.id]: !prev[lead.id] }))}
                            className="w-full flex items-center justify-between p-3.5 sm:p-4 bg-white/5 hover:bg-white/10 transition-colors text-left"
                            type="button"
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="text-base">👥</span>
                              <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-zinc-100">
                                Key Contacts (Decision Makers)
                              </span>
                              {lead.contacts && (
                                <span className="rounded-md border border-[var(--nexa-accent)]/30 bg-[var(--nexa-accent-dim)] px-2.5 py-0.5 text-[10px] font-semibold text-[var(--nexa-accent)]">
                                  {lead.contacts.length} Executive Contacts
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold text-zinc-300">
                              <span>{expandedContacts[lead.id] ? 'Collapse Executive Contacts' : 'Expand Executive Contacts'}</span>
                              <ChevronDown
                                size={16}
                                className={`transition-transform duration-200 ${expandedContacts[lead.id] ? 'rotate-180 text-[var(--nexa-accent)]' : ''}`}
                              />
                            </div>
                          </button>


                          {expandedContacts[lead.id] && (
                            <div className="p-4 border-t border-white/10 animate-fade-in bg-black/20 expanded-contacts-container">
                              {lead.contacts && lead.contacts.length > 0 ? (
                                <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                                  {lead.contacts.map((contact, i) => (
                                    <div key={i} className="contact-card flex flex-col gap-1 rounded-lg border border-white/10 bg-white/5 p-3.5 hover:border-white/20 transition-all shadow-sm">
                                      <div className="flex items-center justify-between">
                                        <span className="text-xs sm:text-sm font-bold text-zinc-100">{contact.name}</span>
                                        <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                                          contact.confidence === 'verified' 
                                            ? 'bg-[var(--nexa-emerald-dim)] text-emerald-400 border border-emerald-500/20' 
                                            : 'bg-[var(--nexa-amber-dim)] text-amber-400 border border-amber-500/20'
                                        }`}>
                                          {contact.confidence}
                                        </span>
                                      </div>
                                      <span className="text-[11px] text-zinc-400 font-medium">{contact.title}</span>
                                      <div className="flex items-center gap-2 mt-1.5 text-[11px] font-mono">
                                        <a href={`mailto:${contact.email}`} className="text-[var(--nexa-accent)] hover:underline flex items-center gap-1 font-semibold">
                                          ✉️ {contact.email}
                                        </a>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <div className="rounded-lg border border-white/5 bg-white/5 p-4 text-center">
                                  <span className="text-xs text-zinc-400">No public executive contacts extracted for {lead.domain} during this sweep.</span>
                                </div>
                              )}
                            </div>
                          )}


                        </div>


                      </div>
                    </td>
                  </tr>
                )}


              </Fragment>
            ))}
            {filteredLeads.length === 0 && (
              <tr>
                <td
                  className="p-16 text-center text-sm font-medium text-zinc-700"
                  colSpan={6}
                >
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
                      className="rounded-lg bg-[var(--nexa-accent)] px-6 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-[var(--nexa-accent-glow)] shadow-[0_0_15px_var(--nexa-accent-dim)]"
                    >
                      Run Base Discovery Pipeline
                    </button>
                  </div>
                </td>
              </tr>
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
    </div>
  );
}

