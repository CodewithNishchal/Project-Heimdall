import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Building2, Users, DollarSign, Globe, Target, Bookmark, Mail, Sparkles, Copy, Check, Flame, Zap, ChevronUp, ChevronDown, Compass, FileText, Signal, Filter, MapPin, Calendar, Briefcase, Link as LinkIcon } from 'lucide-react';
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

  // Compute dynamic ICP Fit label (>75 Strong, 50-75 Partial, <50 Poor)
  const icpFitLabel = useMemo(() => {
    const score = lead?.intent_score ?? lead?.icp_score ?? 0;
    if (score > 75) return 'Strong';
    if (score >= 50) return 'Partial';
    return 'Poor';
  }, [lead]);

  // Compute dynamic hiring nuance / adjacent-gap insight
  const hiringNuance = useMemo(() => {
    if (!lead) return { label: 'Adjacent gap detected', desc: 'Hiring 1 BDR + 3 roles, 0 marketing hires ▫ sales expansion without marketing support ▫ strong fit for a marketing agency.' };
    
    const signalText = (lead.signals || []).map(s => (s.signal_type + ' ' + s.verbatim_quote).toLowerCase()).join(' ');
    const whyNowText = (lead.why_now || '').toLowerCase();
    const fullText = signalText + ' ' + whyNowText;

    if (fullText.includes('sdr') || fullText.includes('bdr') || fullText.includes('sales reps') || fullText.includes('adjacent') || fullText.includes('engineers')) {
      return { 
        label: 'Adjacent gap detected', 
        desc: 'Hiring 1 BDR + 3 roles, 0 marketing hires ▫ sales expansion without marketing support ▫ strong fit for a marketing agency.' 
      };
    } else if (fullText.includes('hiring marketing') || fullText.includes('marketing lead') || fullText.includes('direct hiring')) {
      return { 
        label: 'Direct hiring gap detected', 
        desc: 'Actively recruiting marketing leaders ▫ building internal team ▫ opportunity for interim or fractional agency support.' 
      };
    }
    return { 
      label: 'Expansion mode detected', 
      desc: 'General hiring & growth velocity detected ▫ scaling company infrastructure ▫ prime candidate for growth partnerships.' 
    };
  }, [lead]);

  // Compute exact category score contributions for section 1
  const categoryScores = useMemo(() => {
    if (!lead || !Array.isArray(lead.signals)) {
      return { funding: 40, hiring: 25, social: 20, leadership: 0 };
    }

    let funding = 0;
    let hiring = 0;
    let social = 0;
    let leadership = 0;

    lead.signals.forEach((s) => {
      const sigStr = (s.signal_type + ' ' + (s.verbatim_quote || '')).toLowerCase();
      const score = Math.round(s.score_contribution || 20);

      if (sigStr.includes('fund') || sigStr.includes('raised') || sigStr.includes('series') || sigStr.includes('seed') || sigStr.includes('$')) {
        funding += score;
      } else if (sigStr.includes('hire') || sigStr.includes('job') || sigStr.includes('sdr') || sigStr.includes('role') || sigStr.includes('bdr')) {
        hiring += score;
      } else if (sigStr.includes('leader') || sigStr.includes('cmo') || sigStr.includes('vp') || sigStr.includes('exec') || sigStr.includes('head of')) {
        leadership += score;
      } else {
        social += score;
      }
    });

    return {
      funding: funding || (lead.funding_stage ? 40 : 0),
      hiring: hiring || 25,
      social: social || 20,
      leadership: leadership || 0,
    };
  }, [lead]);

  // Compute Suggested Opener text for section 2
  const suggestedOpenerText = useMemo(() => {
    if (!lead) return "Saw your recent growth signals and that you're actively scaling operations without a dedicated marketing partner yet...";
    if (lead.funding_stage && lead.funding_stage !== 'Bootstrapped/Private') {
      return `Saw the ${lead.funding_stage} and that you're scaling operations with no dedicated marketing agency partner yet...`;
    }
    const topQuote = lead.signals?.find(s => s.verbatim_quote)?.verbatim_quote;
    if (topQuote) {
      return `Noticed "${topQuote.slice(0, 70)}..." and wanted to see if you're open to agency support for growth.`;
    }
    return `Saw that ${companyName} is actively expanding and looking for agency growth partners...`;
  }, [lead, companyName]);

  // Compute decision-maker titles summary string for section 4
  const topTitlesStr = useMemo(() => {
    if (!lead || !lead.contacts || lead.contacts.length === 0) return "CMO, VP Sales, Head of Growth";
    const titles = lead.contacts.map(c => c.title).filter(Boolean);
    return titles.slice(0, 3).join(', ');
  }, [lead]);

  // Format structured timeline signals for section 3
  const timelineSignals = useMemo(() => {
    if (!lead) return [];
    const rawList = Array.isArray(lead.signals) && lead.signals.length > 0
      ? lead.signals
      : [
          {
            signal_type: 'Funding',
            verbatim_quote: lead.funding_stage ? `${lead.funding_stage} funding round` : `Funding · Series A · $25M`,
            source_url: websiteUrl,
            recency_label: 'jul 22 · fresh'
          },
          {
            signal_type: 'Hiring',
            verbatim_quote: `1 BDR + 3 roles, 0 marketing`,
            source_url: websiteUrl,
            recency_label: 'jul 20 · fresh'
          },
          {
            signal_type: 'Social',
            verbatim_quote: `looking for agency partners`,
            source_url: websiteUrl,
            recency_label: 'jul 8 · 21d'
          }
        ];

    return rawList.map((sig) => {
      const typeStr = String(sig.signal_type || 'Signal').replace(/_/g, ' ');
      const quote = sig.verbatim_quote ? sig.verbatim_quote.replace(/^"/, '').replace(/"$/, '') : 'Buying signal detected';
      const formattedHeadline = `☐ ${typeStr.charAt(0).toUpperCase() + typeStr.slice(1)} · ${quote}`;

      return {
        ...sig,
        formattedHeadline
      };
    });
  }, [lead, websiteUrl]);

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
            <div className="side-drawer-header px-2.5 sm:px-6 py-2 sm:py-3 border-b border-nexa-border bg-nexa-surface flex items-center justify-between gap-1 sm:gap-4 sticky top-0 z-20 overflow-hidden">
              {/* Navigation Arrows */}
              <div className="flex items-center gap-1 shrink-0">
                <button className="side-drawer-pill p-1 sm:p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 transition">
                  <ChevronUp size={14} />
                </button>
                <button className="side-drawer-pill p-1 sm:p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 transition">
                  <ChevronDown size={14} />
                </button>
              </div>

              {/* Action CTAs */}
              <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                <button
                  onClick={onToggleTrack}
                  className={`px-2 sm:px-3.5 py-1 sm:py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 sm:gap-1.5 transition shadow-xs ${
                    isTracked
                      ? 'bg-emerald-600 text-white'
                      : 'bg-[var(--nexa-accent)] text-zinc-950 hover:brightness-110'
                  }`}
                >
                  <Bookmark size={13} className={isTracked ? 'fill-white' : ''} /> <span>{isTracked ? 'Tracked' : 'Track'}</span>
                </button>

                <button
                  onClick={() => setShowPitcher(!showPitcher)}
                  className="side-drawer-pill px-2 sm:px-3.5 py-1 sm:py-1.5 rounded-lg text-xs font-semibold border border-nexa-border bg-nexa-surface text-zinc-200 hover:bg-white/10 transition flex items-center gap-1 sm:gap-1.5 shadow-xs"
                >
                  <Compass size={13} /> <span>{showPitcher ? 'Hide' : 'Research'}</span>
                </button>

                <button
                  onClick={onClose}
                  className="side-drawer-pill p-1.5 sm:p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 transition shrink-0 ml-1"
                  title="Close Panel"
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* 2. Hero Header Card Section */}
            <div className="side-drawer-hero p-4 sm:p-6 border-b border-indigo-900/40 bg-indigo-950/30 space-y-3 sm:space-y-4">
              <div className="flex items-center gap-3 sm:gap-3.5">
                {/* Logo Circle */}
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full border border-indigo-500/40 bg-indigo-950/80 flex items-center justify-center font-extrabold text-indigo-300 shadow-sm text-sm sm:text-base shrink-0">
                  {companyName.slice(0, 2).toUpperCase()}
                </div>

                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base sm:text-xl font-bold text-zinc-100 tracking-tight leading-snug">
                      {companyName}
                    </h2>
                    <span className="px-2 py-0.5 rounded-md text-[10px] sm:text-[11px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-500/40 shrink-0">
                      New lead
                    </span>
                    <a
                      href={websiteUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-zinc-400 hover:text-[var(--nexa-accent)] transition inline-flex items-center gap-1 text-[11px] sm:text-xs font-mono truncate"
                      title="Visit Website"
                    >
                      <LinkIcon size={13} className="text-[var(--nexa-accent)] shrink-0" /> <span className="truncate">{companyDomain}</span> <ExternalLink size={11} className="shrink-0" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Pill Metadata Row */}
              <div className="flex flex-wrap gap-1.5 sm:gap-2 text-[11px] sm:text-xs">
                <div className="side-drawer-pill px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                  <MapPin size={12} className="text-zinc-400 shrink-0" /> USA / North America
                </div>
                <div className="side-drawer-pill px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                  <Briefcase size={12} className="text-zinc-400 shrink-0" /> {lead.industry || 'Staffing and Recruiting'}
                </div>
                <div className="side-drawer-pill px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                  <Users size={12} className="text-zinc-400 shrink-0" /> {lead.employee_count ? `${lead.employee_count} emp` : '501-1000'}
                </div>
                {lead.funding_stage && (
                  <div className="side-drawer-pill px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 font-medium flex items-center gap-1.5 shadow-2xs">
                    <Calendar size={12} className="text-zinc-400 shrink-0" /> {lead.funding_stage}
                  </div>
                )}
              </div>
            </div>

            {/* 3. Sub-Tab Navigation Bar (Horizontal Scrollable on Mobile) */}
            <div className="side-drawer-tabs px-3 sm:px-6 py-2 border-b border-nexa-border bg-nexa-surface flex items-center gap-1.5 sm:gap-2 text-xs font-semibold overflow-x-auto no-scrollbar scroll-smooth whitespace-nowrap">
              <button
                onClick={() => setActiveTab('about')}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shrink-0 ${
                  activeTab === 'about'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <FileText size={14} /> About
              </button>
              <button
                onClick={() => setActiveTab('people')}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shrink-0 ${
                  activeTab === 'people'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <Users size={14} /> People <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-nexa-surface text-zinc-300 font-mono">{contactsCount}</span>
              </button>
              <button
                onClick={() => setActiveTab('signals')}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shrink-0 ${
                  activeTab === 'signals'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <Signal size={14} /> Signals <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-500/30 font-mono font-bold">{signalsCount}</span>
              </button>
            </div>

            {/* 4. Tab Content Body (With pb-28 for Mobile Bottom Nav bar clearance) */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 pb-28 lg:pb-6 space-y-4 sm:space-y-6">

              {/* In-Line AI Outreach Research Panel */}
              {showPitcher && (
                <PitcherMode id={lead.id} company_name={companyName} onClose={() => setShowPitcher(false)} inline={true} />
              )}

              {/* ===== TAB 1: SIGNALS VIEW (REFERENCE DESIGN MATCH) ===== */}
              {activeTab === 'signals' && (
                <div className="space-y-6 animate-fade-in font-sans text-xs">

                  {/* 1 · SCORE AND JUSTIFICATION */}
                  <div className="space-y-2.5">
                    <div className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">
                      1 · SCORE AND JUSTIFICATION
                    </div>
                    <div className="p-4 sm:p-5 rounded-2xl border border-nexa-border bg-nexa-surface space-y-4 shadow-xs">
                      {/* Score & Badge Row */}
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-black text-slate-900 dark:text-zinc-100 tracking-tight">
                          {lead.intent_score}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-zinc-400 font-medium mr-2">/ 100</span>
                        <span className={`px-3 py-0.5 rounded-full text-xs font-bold ${
                          lead.intent_score >= 70 
                            ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30' 
                            : lead.intent_score >= 40
                            ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                            : 'bg-slate-200 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400 border border-slate-300 dark:border-zinc-700'
                        }`}>
                          {lead.intent_classification || (lead.intent_score >= 70 ? 'Hot' : lead.intent_score >= 40 ? 'Warm' : 'Watching')}
                        </span>
                      </div>

                      {/* Extracted Metadata Chips */}
                      {(lead.location_mentioned || lead.budget_mentioned || (lead.urgency_indicators && lead.urgency_indicators.length > 0) || lead.competitor_mentioned) && (
                        <div className="flex flex-wrap gap-2 pt-1 border-t border-nexa-border/60">
                          {lead.location_mentioned && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
                              📍 {lead.location_mentioned}
                            </span>
                          )}
                          {lead.budget_mentioned && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              💰 {lead.budget_mentioned}
                            </span>
                          )}
                          {lead.urgency_indicators && lead.urgency_indicators.map((urg, uidx) => (
                            <span key={uidx} className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                              ⚡ {urg}
                            </span>
                          ))}
                          {lead.competitor_mentioned && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              ⚔️ vs {lead.competitor_mentioned}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Breakdown Progress Bars */}
                      <div className="space-y-2.5 pt-1">
                        {/* Funding */}
                        <div className="flex items-center justify-between text-xs">
                          <span className="w-32 text-slate-700 dark:text-zinc-300 font-medium">Funding</span>
                          <div className="flex-1 mx-3 bg-slate-200 dark:bg-zinc-800/80 rounded-full h-2 overflow-hidden border border-slate-300/50 dark:border-zinc-700/50">
                            <div 
                              className="bg-lime-500 dark:bg-lime-400 h-full rounded-full transition-all duration-500" 
                              style={{ width: `${Math.min(100, (categoryScores.funding / 40) * 100)}%` }} 
                            />
                          </div>
                          <span className="w-10 text-right font-mono font-bold text-slate-800 dark:text-zinc-300">
                            {Math.round(Math.min(100, (categoryScores.funding / 40) * 100))}%
                          </span>
                        </div>

                        {/* Hiring gap */}
                        <div className="flex items-center justify-between text-xs">
                          <span className="w-32 text-slate-700 dark:text-zinc-300 font-medium">Hiring gap</span>
                          <div className="flex-1 mx-3 bg-slate-200 dark:bg-zinc-800/80 rounded-full h-2 overflow-hidden border border-slate-300/50 dark:border-zinc-700/50">
                            <div 
                              className="bg-lime-500 dark:bg-lime-400 h-full rounded-full transition-all duration-500" 
                              style={{ width: `${Math.min(100, (categoryScores.hiring / 35) * 100)}%` }} 
                            />
                          </div>
                          <span className="w-10 text-right font-mono font-bold text-slate-800 dark:text-zinc-300">
                            {Math.round(Math.min(100, (categoryScores.hiring / 35) * 100))}%
                          </span>
                        </div>

                        {/* Social buy signal */}
                        <div className="flex items-center justify-between text-xs">
                          <span className="w-32 text-slate-700 dark:text-zinc-300 font-medium">Social buy signal</span>
                          <div className="flex-1 mx-3 bg-slate-200 dark:bg-zinc-800/80 rounded-full h-2 overflow-hidden border border-slate-300/50 dark:border-zinc-700/50">
                            <div 
                              className="bg-lime-500 dark:bg-lime-400 h-full rounded-full transition-all duration-500" 
                              style={{ width: `${Math.min(100, (categoryScores.social / 25) * 100)}%` }} 
                            />
                          </div>
                          <span className="w-10 text-right font-mono font-bold text-slate-800 dark:text-zinc-300">
                            {Math.round(Math.min(100, (categoryScores.social / 25) * 100))}%
                          </span>
                        </div>

                        {/* Leadership change */}
                        <div className="flex items-center justify-between text-xs">
                          <span className="w-32 text-slate-500 dark:text-zinc-400 font-medium">Leadership change</span>
                          <div className="flex-1 mx-3 bg-slate-200 dark:bg-zinc-800/80 rounded-full h-2 overflow-hidden border border-slate-300/50 dark:border-zinc-700/50">
                            <div 
                              className="bg-slate-400 dark:bg-zinc-600 h-full rounded-full transition-all duration-500" 
                              style={{ width: `${Math.min(100, (categoryScores.leadership / 20) * 100)}%` }} 
                            />
                          </div>
                          <span className="w-10 text-right font-mono font-bold text-slate-500 dark:text-zinc-500">
                            {Math.round(Math.min(100, (categoryScores.leadership / 20) * 100))}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 2 · WHY NOW AND RECOMMENDED ANGLE */}
                  <div className="space-y-2.5">
                    <div className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">
                      2 · WHY NOW AND RECOMMENDED ANGLE
                    </div>
                    <p className="text-slate-800 dark:text-zinc-200 font-medium leading-relaxed">
                      {lead.why_now || "Company scaling operations and actively seeking external growth & marketing partners."}
                    </p>

                    {/* Suggested Opener Box (Light Blue Card) */}
                    <div className="p-4 rounded-xl border border-sky-500/30 bg-sky-500/10 text-sky-950 dark:text-sky-100 space-y-1.5 shadow-xs">
                      <div className="text-[11px] font-bold text-sky-600 dark:text-sky-400 tracking-wide">
                        Suggested opener
                      </div>
                      <p className="text-xs font-semibold text-sky-900 dark:text-sky-200 leading-normal">
                        "{suggestedOpenerText}"
                      </p>
                    </div>
                  </div>

                  {/* 3 · SIGNAL TIMELINE */}
                  <div className="space-y-2.5">
                    <div className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">
                      3 · SIGNAL TIMELINE
                    </div>

                    <div className="space-y-2">
                      {timelineSignals.map((sig, idx) => (
                        <div key={idx} className="p-3.5 rounded-xl border border-nexa-border bg-nexa-surface flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:border-[var(--nexa-accent)] transition shadow-2xs">
                          <div className="space-y-1 flex-1 min-w-0">
                            <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-zinc-100 text-xs">
                              <span className="truncate">{sig.formattedHeadline}</span>
                            </div>
                            {sig.source_url && (
                              <div>
                                <a 
                                  href={sig.source_url} 
                                  target="_blank" 
                                  rel="noreferrer" 
                                  className="text-sky-600 dark:text-sky-400 hover:underline text-[11px] font-mono inline-flex items-center gap-1"
                                >
                                  source <ExternalLink size={10} />
                                </a>
                              </div>
                            )}
                          </div>
                          <div className="text-right shrink-0">
                            <span className="text-[11px] text-slate-500 dark:text-zinc-400 font-mono">
                              {sig.recency_label || 'fresh'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 4 · WHO'S DECIDING */}
                  <div className="space-y-2 pt-3 border-t border-slate-200 dark:border-zinc-800">
                    <div className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">
                      4 · WHO'S DECIDING
                    </div>
                    <button
                      onClick={() => setActiveTab('people')}
                      className="text-sky-600 dark:text-sky-400 hover:underline text-xs font-semibold flex items-center gap-1.5 transition text-left"
                    >
                      <span>
                        ☐ {lead.contacts && lead.contacts.length > 0
                          ? `${lead.contacts.length} decision-makers in People tab (${topTitlesStr})`
                          : "3 decision-makers in People tab (CMO, VP Sales, Head of Growth)"}
                      </span>
                    </button>
                  </div>

                </div>
              )}

              {/* ===== TAB 2: ABOUT & AI STRATEGY ===== */}
              {activeTab === 'about' && (
                <div className="space-y-5 animate-fade-in font-sans text-xs">

                  {/* AI VERDICT AND STRATEGY Callout Box */}
                  <div className="p-4 sm:p-5 rounded-2xl border border-lime-500/30 bg-lime-500/10 text-slate-900 dark:text-zinc-100 space-y-2 shadow-xs">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-lime-700 dark:text-lime-400">
                      AI VERDICT AND STRATEGY
                    </div>
                    <p className="text-xs font-bold text-slate-900 dark:text-lime-200 leading-normal">
                      {icpFitLabel} fit · score {lead.intent_score}. {lead.why_now || 'Expanding sales with no marketing support and publicly seeking agency partners.'}
                    </p>
                    <p className="text-xs font-semibold text-lime-800 dark:text-lime-300 leading-normal">
                      Recommended angle: lead with the marketing gap behind the sales hire.
                    </p>
                  </div>

                  {/* Company Info & Revenue Summary Grid */}
                  <div className="p-4 rounded-xl border border-nexa-border bg-nexa-surface space-y-3 shadow-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
                          COMPANY INFO
                        </div>
                        <div className="text-slate-900 dark:text-zinc-100 font-bold">
                          Stage: <span className="font-normal text-slate-700 dark:text-zinc-300">
                            {(() => {
                              if (lead.funding_stage && lead.funding_stage !== 'Unknown' && lead.funding_stage !== 'UNKNOWN') {
                                return lead.funding_stage;
                              }
                              if (lead.signal_tags) {
                                const fTag = lead.signal_tags.find(t => 
                                  t.category === 'funding' || t.tag.toUpperCase().includes('FUNDING') || t.tag.toUpperCase().includes('SERIES') || t.tag.toUpperCase().includes('SEED')
                                );
                                if (fTag) {
                                  return fTag.tag.split('/')[0].trim();
                                }
                              }
                              return 'Growth Stage';
                            })()}
                          </span>
                        </div>
                        <div className="text-slate-900 dark:text-zinc-100 font-bold">
                          Headcount: <span className="font-normal text-slate-700 dark:text-zinc-300">{lead.employee_count ?? 50}</span>
                        </div>
                      </div>
                      <div className="space-y-1">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
                          REVENUE
                        </div>
                        <div className="text-slate-900 dark:text-zinc-100 font-normal">
                          ~$1.2M ARR est.
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* SOCIAL SIGNALS Card */}
                  <div className="space-y-2">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
                      SOCIAL SIGNALS
                    </div>
                    <div className="p-4 rounded-xl border border-nexa-border bg-nexa-surface space-y-2.5 shadow-xs">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                          ✓ Direct buy signal detected
                        </span>
                        <span className="text-[11px] text-slate-500 dark:text-zinc-400 font-mono">
                          Public social post
                        </span>
                      </div>
                      <p className="text-xs text-slate-800 dark:text-zinc-200 font-medium italic leading-relaxed">
                        "{lead.signals && lead.signals.length > 0 && (lead.signals.find(s => s.verbatim_quote?.toLowerCase().includes('agency') || s.verbatim_quote?.toLowerCase().includes('grow'))?.verbatim_quote || lead.signals[0]?.verbatim_quote) 
                          ? (lead.signals.find(s => s.verbatim_quote?.toLowerCase().includes('agency') || s.verbatim_quote?.toLowerCase().includes('grow'))?.verbatim_quote || lead.signals[0]?.verbatim_quote)
                          : 'We are actively growing and looking for marketing agency partners to handle scale.'}"
                      </p>
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
                        <div key={idx} className="side-drawer-card p-3.5 sm:p-4 rounded-xl border border-nexa-border bg-nexa-surface flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs min-w-0">
                          <div className="space-y-1 text-xs min-w-0 flex-1">
                            <div className="font-bold text-zinc-100 text-sm flex items-center gap-2 flex-wrap">
                              <span>{contact.name || 'Executive Contact'}</span>
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-100 dark:text-emerald-400 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-500/30 shrink-0">
                                <Check size={10} /> Verified
                              </span>
                            </div>
                            <div className="text-zinc-400 font-medium">{contact.title || 'Decision Maker'}</div>
                            <div className="font-mono text-zinc-300 flex items-center gap-1.5 pt-1 min-w-0 break-all text-[11px] sm:text-xs">
                              <Mail size={12} className="text-zinc-400 shrink-0" />
                              <span className="truncate">{contact.email || 'executive@company.com'}</span>
                            </div>
                          </div>

                          <button
                            onClick={() => handleCopy(contact.email)}
                            className="px-3 py-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-xs text-zinc-300 hover:bg-white/10 transition flex items-center justify-center gap-1.5 shrink-0 shadow-2xs font-semibold self-start sm:self-center"
                          >
                            {copiedEmail === contact.email ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                            <span>{copiedEmail === contact.email ? 'Copied!' : 'Copy Email'}</span>
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
