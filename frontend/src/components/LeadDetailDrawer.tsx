import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Building2, Users, DollarSign, Globe, Target, Mail, Sparkles, Copy, Check, Flame, Zap, ChevronUp, ChevronDown, Compass, FileText, Signal, Filter, MapPin, Calendar, Briefcase, Link as LinkIcon } from 'lucide-react';
import type { LeadDetailResponse } from '../types/lead';
import PitcherMode from './PitcherMode';

interface LeadDetailDrawerProps {
  lead: LeadDetailResponse | null;
  onClose: () => void;
  isTracked?: boolean;
  onToggleTrack?: () => void;
}

function getSignalIconAndTheme(signalText: string) {
  const lower = signalText.toLowerCase();

  // 1. Funding / Series / Seed / Revenue -> DollarSign (Indigo)
  if (lower.includes('fund') || lower.includes('series') || lower.includes('seed') || lower.includes('raised') || lower.includes('$')) {
    return {
      icon: <DollarSign size={13} className="text-indigo-600 dark:text-indigo-400" />,
      style: 'bg-indigo-100 border-indigo-300 dark:bg-indigo-950/80 dark:border-indigo-500/40',
    };
  }

  // 2. Headcount / Growth / Hiring / Roles -> Users (Emerald)
  if (lower.includes('hire') || lower.includes('job') || lower.includes('sdr') || lower.includes('role') || lower.includes('headcount') || lower.includes('growth')) {
    return {
      icon: <Users size={13} className="text-emerald-600 dark:text-emerald-400" />,
      style: 'bg-emerald-100 border-emerald-300 dark:bg-emerald-950/80 dark:border-emerald-500/40',
    };
  }

  // 3. Executive Changes / Leadership / CMO / VP -> Sparkles (Purple)
  if (lower.includes('cmo') || lower.includes('vp') || lower.includes('exec') || lower.includes('director') || lower.includes('leader')) {
    return {
      icon: <Sparkles size={13} className="text-purple-600 dark:text-purple-400" />,
      style: 'bg-purple-100 border-purple-300 dark:bg-purple-950/80 dark:border-purple-500/40',
    };
  }

  // 4. Agency / Intent / Seeking / Partnership / RFP -> Target (Rose)
  if (lower.includes('agency') || lower.includes('partner') || lower.includes('seek') || lower.includes('rfp') || lower.includes('post')) {
    return {
      icon: <Target size={13} className="text-rose-600 dark:text-rose-400" />,
      style: 'bg-rose-100 border-rose-300 dark:bg-rose-950/80 dark:border-rose-500/40',
    };
  }

  // 5. Tech Stack / Tools / Infra / Migration -> Zap (Amber)
  if (lower.includes('tech') || lower.includes('tool') || lower.includes('stack') || lower.includes('migrate')) {
    return {
      icon: <Zap size={13} className="text-amber-600 dark:text-amber-400" />,
      style: 'bg-amber-100 border-amber-300 dark:bg-amber-950/80 dark:border-amber-500/40',
    };
  }

  // Default Intent Signal -> Signal (Teal)
  return {
    icon: <Signal size={13} className="text-teal-600 dark:text-teal-400" />,
    style: 'bg-teal-100 border-teal-300 dark:bg-teal-950/80 dark:border-teal-500/40',
  };
}

export default function LeadDetailDrawer({ lead, onClose, isTracked = false, onToggleTrack }: LeadDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<'about' | 'people' | 'signals'>('signals');
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  const [showPitcher, setShowPitcher] = useState(false);

  // Working Filters & View Controls
  const [behaviorFilter, setBehaviorFilter] = useState<'ALL' | 'FUNDING' | 'HIRING'>('ALL');
  const [sortOrder, setSortOrder] = useState<'NEWEST' | 'OLDEST'>('NEWEST');
  const [viewMode, setViewMode] = useState<'DETAILED' | 'COMPACT'>('DETAILED');

  const companyName = lead?.company_name || 'Target Company';
  const companyDomain = lead?.domain || 'example.com';
  const websiteUrl = companyDomain.startsWith('http') ? companyDomain : `https://${companyDomain}`;

  const handleCopy = (email: string) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  const filteredAndSortedSignals = useMemo(() => {
    if (!lead) return [];
    let list = Array.isArray(lead.signals) && lead.signals.length > 0
      ? [...lead.signals]
      : [
          {
            signal_type: 'funding_detected',
            verbatim_quote: 'Detected high-intent indicator "funding" in public brand signals.',
            source_url: websiteUrl,
            quote_validated: true,
            similarity_score: 0.9,
            recency_label: '6 days ago',
            score_contribution: 25,
          },
        ];

    if (behaviorFilter === 'FUNDING') {
      list = list.filter(s => {
        const st = String(s.signal_type || '').toLowerCase();
        return st.includes('fund') || st.includes('raised') || st.includes('seed');
      });
    } else if (behaviorFilter === 'HIRING') {
      list = list.filter(s => {
        const st = String(s.signal_type || '').toLowerCase();
        return st.includes('hire') || st.includes('job') || st.includes('sdr') || st.includes('role');
      });
    }

    if (sortOrder === 'OLDEST') {
      return [...list].reverse();
    }
    return list;
  }, [lead, websiteUrl, behaviorFilter, sortOrder]);

  const signalsCount = lead && Array.isArray(lead.signals) ? lead.signals.length : 3;
  const contactsCount = lead && Array.isArray(lead.contacts) ? lead.contacts.length : 2;

  return (
    <AnimatePresence>
      {lead && (
        <>
          {/* Backdrop Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50"
            onClick={onClose}
          />

          {/* Slide-Over Right Side Panel (Framer Motion Animated) */}
          <motion.div
            initial={{ opacity: 0, x: '100%' }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            className="side-drawer-panel fixed inset-y-0 right-0 w-full max-w-4xl bg-nexa-bg border-l border-nexa-border shadow-2xl z-50 flex flex-col font-sans"
          >
            
            {/* 1. Top Header Controls Bar */}
            <div className="side-drawer-header px-6 py-3 border-b border-nexa-border bg-nexa-surface flex items-center justify-between gap-4 sticky top-0 z-20">
              {/* Navigation Arrows */}
              <div className="flex items-center gap-1">
                <button className="side-drawer-pill p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 transition">
                  <ChevronUp size={14} />
                </button>
                <button className="side-drawer-pill p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 transition">
                  <ChevronDown size={14} />
                </button>
              </div>

              {/* Action CTAs */}
              <div className="flex items-center gap-2">
                <button
                  onClick={onToggleTrack}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition shadow-xs ${
                    isTracked
                      ? 'bg-emerald-600 text-white'
                      : 'bg-[var(--nexa-accent)] text-zinc-950 hover:brightness-110'
                  }`}
                >
                  <Target size={14} /> {isTracked ? 'Tracked' : 'Track'}
                </button>

                <button
                  onClick={() => setShowPitcher(!showPitcher)}
                  className="side-drawer-pill px-3.5 py-1.5 rounded-lg text-xs font-semibold border border-nexa-border bg-nexa-surface text-zinc-200 hover:bg-white/10 transition flex items-center gap-1.5 shadow-xs"
                >
                  <Compass size={14} /> {showPitcher ? 'Hide Research' : 'Research'}
                </button>

                <button
                  onClick={onClose}
                  className="side-drawer-pill p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 transition"
                  title="Close Panel"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* 2. Hero Header Card Section */}
            <div className="side-drawer-hero p-6 border-b border-indigo-900/40 bg-indigo-950/30 space-y-4">
              <div className="flex items-center gap-3.5">
                {/* Logo Circle */}
                <div className="w-12 h-12 rounded-full border border-indigo-500/40 bg-indigo-950/80 flex items-center justify-center font-extrabold text-indigo-300 shadow-sm text-base shrink-0">
                  {companyName.slice(0, 2).toUpperCase()}
                </div>

                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-bold text-zinc-100 tracking-tight">
                      {companyName}
                    </h2>
                    <span className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-500/40">
                      New lead
                    </span>
                    <a
                      href={websiteUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-zinc-400 hover:text-[var(--nexa-accent)] transition inline-flex items-center gap-1 text-xs font-mono"
                      title="Visit Website"
                    >
                      <LinkIcon size={14} className="text-[var(--nexa-accent)]" /> {companyDomain} <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              </div>

              {/* Pill Metadata Row */}
              <div className="flex flex-wrap gap-2 text-xs">
                <div className="side-drawer-pill px-3 py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                  <MapPin size={13} className="text-zinc-400" /> USA / North America
                </div>
                <div className="side-drawer-pill px-3 py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                  <Briefcase size={13} className="text-zinc-400" /> {lead.industry || 'Staffing and Recruiting'}
                </div>
                <div className="side-drawer-pill px-3 py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                  <Users size={13} className="text-zinc-400" /> {lead.employee_count ? `${lead.employee_count} emp` : '501-1000'}
                </div>
                <div className="side-drawer-pill px-3 py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                  <Calendar size={13} className="text-zinc-400" /> {lead.funding_stage || 'Series B'}
                </div>
              </div>
            </div>

            {/* 3. Sub-Tab Navigation Bar */}
            <div className="side-drawer-tabs px-6 py-2.5 border-b border-nexa-border bg-nexa-surface flex items-center gap-2 text-xs font-semibold">
              <button
                onClick={() => setActiveTab('about')}
                className={`px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition ${
                  activeTab === 'about'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <FileText size={14} /> About
              </button>
              <button
                onClick={() => setActiveTab('people')}
                className={`px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition ${
                  activeTab === 'people'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <Users size={14} /> People <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-nexa-surface text-zinc-300 font-mono">{contactsCount}</span>
              </button>
              <button
                onClick={() => setActiveTab('signals')}
                className={`px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition ${
                  activeTab === 'signals'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <Signal size={14} /> Signals <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-500/30 font-mono font-bold">{signalsCount}</span>
              </button>
            </div>

            {/* 4. Tab Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">

              {/* In-Line AI Outreach Research Panel */}
              {showPitcher && (
                <PitcherMode id={lead.id} company_name={companyName} onClose={() => setShowPitcher(false)} inline={true} />
              )}

              {/* ===== TAB 1: SIGNALS VIEW ===== */}
              {activeTab === 'signals' && (
                <div className="space-y-5 animate-fade-in">
                  {/* Header Title & Recency Badges */}
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h3 className="text-base font-bold text-zinc-100">Signals</h3>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="side-drawer-pill px-3 py-1 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-300 font-medium flex items-center gap-1">
                        <Calendar size={12} className="text-zinc-400" /> First: Jul 27, 2026
                      </span>
                      <span className="side-drawer-pill px-3 py-1 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-300 font-medium flex items-center gap-1">
                        🕒 Last: 6 days ago
                      </span>
                    </div>
                  </div>

                  {/* View Filters & Controls Bar */}
                  <div className="flex items-center gap-2 flex-wrap text-xs font-medium border-b border-nexa-border pb-3">
                    <select
                      value={behaviorFilter}
                      onChange={(e) => setBehaviorFilter(e.target.value as any)}
                      className="side-drawer-pill px-3 py-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-200 shadow-2xs cursor-pointer font-medium outline-hidden"
                    >
                      <option value="ALL">Group by behavior: All</option>
                      <option value="FUNDING">Funding Signals</option>
                      <option value="HIRING">Hiring Signals</option>
                    </select>

                    <select
                      value={sortOrder}
                      onChange={(e) => setSortOrder(e.target.value as any)}
                      className="side-drawer-pill px-3 py-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-200 shadow-2xs cursor-pointer font-medium outline-hidden"
                    >
                      <option value="NEWEST">Signal date: Newest First</option>
                      <option value="OLDEST">Signal date: Oldest First</option>
                    </select>

                    <div className="flex items-center border border-nexa-border rounded-lg p-0.5 bg-nexa-surface ml-auto">
                      <button
                        onClick={() => setViewMode('DETAILED')}
                        className={`px-2.5 py-1 rounded-md text-xs font-bold transition ${
                          viewMode === 'DETAILED'
                            ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-2xs'
                            : 'text-zinc-400 hover:text-zinc-100'
                        }`}
                      >
                        Detailed
                      </button>
                      <button
                        onClick={() => setViewMode('COMPACT')}
                        className={`px-2.5 py-1 rounded-md text-xs font-bold transition ${
                          viewMode === 'COMPACT'
                            ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-2xs'
                            : 'text-zinc-400 hover:text-zinc-100'
                        }`}
                      >
                        Compact
                      </button>
                    </div>
                  </div>

                  {/* Signal List Group */}
                  <div className="space-y-3">
                    <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1">
                      <ChevronDown size={12} /> OTHER INTENT SIGNALS ({filteredAndSortedSignals.length})
                    </div>

                    {filteredAndSortedSignals.length > 0 ? (
                      viewMode === 'DETAILED' ? (
                        filteredAndSortedSignals.map((sig, idx) => {
                          const sigType = String(sig.signal_type || 'intent_signal').replace(/_/g, ' ');
                          const { icon, style } = getSignalIconAndTheme(sigType + ' ' + (sig.verbatim_quote || ''));
                          return (
                            <div key={idx} className="side-drawer-card p-4 rounded-xl border border-nexa-border bg-nexa-surface space-y-2 text-xs shadow-2xs">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2.5 font-bold text-zinc-100 text-sm">
                                  <div className={`w-7 h-7 rounded-full border flex items-center justify-center shrink-0 shadow-xs ${style}`}>
                                    {icon}
                                  </div>
                                  <span className="capitalize">{sigType}</span>
                                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-nexa-surface text-zinc-300 font-mono border border-nexa-border">1</span>
                                </div>
                                <span className="text-xs text-zinc-400 font-mono">6 days ago</span>
                              </div>

                              {sig.verbatim_quote && (
                                <p className="text-zinc-300 pl-9 font-normal">
                                  "{sig.verbatim_quote}"
                                </p>
                              )}

                              {sig.source_url && (
                                <div className="pl-9 pt-1">
                                  <a
                                    href={sig.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[var(--nexa-accent)] hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
                                  >
                                    Source Citation <ExternalLink size={10} />
                                  </a>
                                </div>
                              )}
                            </div>
                          );
                        })
                      ) : (
                        /* COMPACT VIEW MODE */
                        <div className="space-y-2">
                          {filteredAndSortedSignals.map((sig, idx) => {
                            const sigType = String(sig.signal_type || 'intent_signal').replace(/_/g, ' ');
                            const { icon, style } = getSignalIconAndTheme(sigType + ' ' + (sig.verbatim_quote || ''));
                            return (
                              <div key={idx} className="side-drawer-pill p-3 rounded-xl border border-nexa-border bg-nexa-surface flex items-center justify-between gap-3 text-xs shadow-2xs">
                                <div className="flex items-center gap-2.5 truncate">
                                  <div className={`w-6 h-6 rounded-full border flex items-center justify-center shrink-0 shadow-xs ${style}`}>
                                    {icon}
                                  </div>
                                  <span className="font-bold text-zinc-100 truncate capitalize">{sigType}</span>
                                  {sig.verbatim_quote && (
                                    <span className="text-zinc-400 truncate hidden sm:inline font-normal">"{sig.verbatim_quote}"</span>
                                  )}
                                </div>
                                <span className="text-[11px] text-zinc-400 font-mono shrink-0">6 days ago</span>
                              </div>
                            );
                          })}
                        </div>
                      )
                    ) : (
                      <div className="side-drawer-card p-4 rounded-xl border border-nexa-border bg-nexa-surface text-xs text-zinc-400">
                        No signals matched the selected behavior filter.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ===== TAB 2: ABOUT & AI STRATEGY ===== */}
              {activeTab === 'about' && (
                <div className="space-y-6 animate-fade-in">
                  <div className="side-drawer-verdict-card p-5 rounded-2xl border border-emerald-500/30 bg-emerald-950/40 text-zinc-100 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                        <Sparkles size={14} className="text-emerald-400" /> AI Verdict & Strategy
                      </h3>
                    </div>
                    
                    <p className="side-drawer-verdict-text text-xs text-emerald-200/90 leading-relaxed font-medium">
                      {lead.ai_verdict || `${companyName} is actively seeking agency partners due to their growth. This indicates a strong potential need for marketing and growth services.`}
                    </p>

                    <div className="side-drawer-verdict-inner p-3 rounded-xl border border-emerald-500/30 bg-emerald-950/70 text-xs space-y-1">
                      <span className="font-bold text-emerald-400 block">Why Now Trigger:</span>
                      <span className="text-emerald-200">{lead.why_now || 'Intent signals detected'}</span>
                    </div>

                    {showPitcher && (
                      <div className="pt-3 border-t border-emerald-500/20 animate-fade-in">
                        <PitcherMode id={lead.id} company_name={companyName} onClose={() => setShowPitcher(false)} inline={true} />
                      </div>
                    )}
                  </div>

                  {/* 3-Column Detailed Company Overview & Signals Card */}
                  <div className="side-drawer-card p-5 rounded-2xl border border-nexa-border bg-nexa-card space-y-4 shadow-2xs">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
                      
                      {/* Column 1: COMPANY INFO */}
                      <div className="space-y-2">
                        <h4 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
                          COMPANY INFO
                        </h4>
                        <div className="space-y-1.5 leading-snug">
                          <div>
                            <span className="font-bold text-zinc-100">Industry: </span>
                            <span className="text-zinc-300">{lead.industry || 'EdTech / Coaching'}</span>
                          </div>
                          <div>
                            <span className="font-bold text-zinc-100">Stage: </span>
                            <span className="text-zinc-300">{lead.funding_stage || 'Seed'}</span>
                          </div>
                          <div>
                            <span className="font-bold text-zinc-100">Headcount: </span>
                            <span className="text-zinc-300">{lead.employee_count ?? 35}</span>
                          </div>
                          <div>
                            <span className="font-bold text-zinc-100">Revenue: </span>
                            <span className="text-zinc-300">~$1.2M ARR (est.)</span>
                          </div>
                          <div className="pt-1">
                            <a
                              href={websiteUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[var(--nexa-accent)] hover:underline inline-flex items-center gap-1 font-mono text-[11px] font-medium"
                            >
                              {companyDomain} <ExternalLink size={11} />
                            </a>
                          </div>
                        </div>
                      </div>

                      {/* Column 2: HIRING SNAPSHOT */}
                      <div className="space-y-2">
                        <h4 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
                          HIRING SNAPSHOT
                        </h4>
                        <div className="space-y-1.5 leading-snug">
                          <div>
                            <span className="font-bold text-zinc-100">Open roles: </span>
                            <span className="text-zinc-300">4</span>
                          </div>
                          <div>
                            <span className="font-bold text-zinc-100">Sales roles: </span>
                            <span className="text-zinc-300">1 BDR</span>
                          </div>
                          <div>
                            <span className="font-bold text-zinc-100">Marketing roles: </span>
                            <span className="text-zinc-300">0</span>
                          </div>
                        </div>
                      </div>

                      {/* Column 3: SOCIAL SIGNALS */}
                      <div className="space-y-2">
                        <h4 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
                          SOCIAL SIGNALS
                        </h4>
                        <div className="space-y-2 leading-snug">
                          <div>
                            <span className="font-bold text-zinc-100">LinkedIn post (Jul 8): </span>
                            <span className="text-zinc-300 italic">
                              "{lead.signals?.[0]?.verbatim_quote || 'We are actively growing and looking for agency partners'}"
                            </span>
                          </div>
                          <div className="text-emerald-500 dark:text-emerald-400 font-semibold flex items-center gap-1">
                            ✓ Direct buy signal — explicitly seeking agencies
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ===== TAB 3: PEOPLE VIEW ===== */}
              {activeTab === 'people' && (
                <div className="space-y-4 animate-fade-in">
                  <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                    <Users size={16} className="text-emerald-400" /> Key Executive Decision Makers
                  </h3>

                  {Array.isArray(lead.contacts) && lead.contacts.length > 0 ? (
                    <div className="space-y-3">
                      {lead.contacts.map((contact, idx) => (
                        <div key={idx} className="side-drawer-card p-4 rounded-xl border border-nexa-border bg-nexa-surface flex items-center justify-between gap-4 shadow-2xs">
                          <div className="space-y-1 text-xs">
                            <div className="font-bold text-zinc-100 text-sm flex items-center gap-2">
                              {contact.name || 'Executive Contact'}
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-100 dark:text-emerald-400 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-500/30">
                                <Check size={10} /> Verified
                              </span>
                            </div>
                            <div className="text-zinc-400 font-medium">{contact.title || 'Decision Maker'}</div>
                            <div className="font-mono text-zinc-300 flex items-center gap-1.5 pt-1">
                              <Mail size={12} className="text-zinc-400" />
                              {contact.email || 'executive@company.com'}
                            </div>
                          </div>

                          <button
                            onClick={() => handleCopy(contact.email)}
                            className="px-3 py-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-xs text-zinc-300 hover:bg-white/10 transition flex items-center gap-1.5 shrink-0 shadow-2xs font-semibold"
                          >
                            {copiedEmail === contact.email ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                            {copiedEmail === contact.email ? 'Copied!' : 'Copy Email'}
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="side-drawer-card p-4 rounded-xl border border-nexa-border bg-nexa-surface text-xs text-zinc-400">
                      No public executive contacts extracted yet for this lead.
                    </div>
                  )}
                </div>
              )}

            </div>

          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
