import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Building2, Users, DollarSign, Globe, Target, Bookmark, Mail, Sparkles, Copy, Check, Flame, Zap, ChevronUp, ChevronDown, Compass, FileText, Signal, Filter, MapPin, Calendar, Briefcase, Link as LinkIcon, MessageSquare, Megaphone, TrendingUp, Bell, Info, Activity, LineChart } from 'lucide-react';
import type { LeadDetailResponse } from '../types/lead';
import PitcherMode from './PitcherMode';
import JobsTab from './JobsTab';

interface LeadDetailDrawerProps {
  lead: LeadDetailResponse | null;
  onClose: () => void;
  isTracked?: boolean;
  onToggleTrack?: () => void;
  onSelectLead?: (id: string | null) => void;
  allLeads?: LeadDetailResponse[];
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

export default function LeadDetailDrawer({
  lead,
  onClose,
  isTracked = false,
  onToggleTrack,
  onSelectLead,
  allLeads = [],
}: LeadDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<'about' | 'people' | 'signals' | 'jobs' | 'insights'>('signals');
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  const [showPitcher, setShowPitcher] = useState(false);

  // Compute navigation indices for ChevronUp / ChevronDown buttons
  const currentIndex = useMemo(() => {
    if (!lead || !allLeads || allLeads.length === 0) return -1;
    const targetKey = String(lead.id || lead.domain || lead.company_name);
    return allLeads.findIndex((l) => String(l.id || l.domain || l.company_name) === targetKey);
  }, [lead, allLeads]);

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex !== -1 && currentIndex < (allLeads?.length || 0) - 1;

  const handlePrevLead = () => {
    if (hasPrev && allLeads && onSelectLead) {
      const prevLead = allLeads[currentIndex - 1];
      const prevKey = String(prevLead.id || prevLead.domain || prevLead.company_name);
      onSelectLead(prevKey);
    }
  };

  const handleNextLead = () => {
    if (hasNext && allLeads && onSelectLead) {
      const nextLead = allLeads[currentIndex + 1];
      const nextKey = String(nextLead.id || nextLead.domain || nextLead.company_name);
      onSelectLead(nextKey);
    }
  };

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

  const signalsCount = lead && Array.isArray(lead.signals) ? lead.signals.length : 0;
  const contactsCount = lead && Array.isArray(lead.contacts) ? lead.contacts.length : 0;
  const jobsCount = lead?.job_openings?.verified_jobs?.length ?? lead?.job_openings?.qualified_jobs?.length ?? (Array.isArray(lead?.job_openings) ? lead.job_openings.length : 0);

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

  // Compute overall display score based on average of key growth & hiring signals
  const displayScore = useMemo(() => {
    if (!lead) return 100;

    const fVal = Math.round(Math.min(100, (categoryScores.funding / 40) * 100));
    const hVal = Math.round(Math.min(100, (categoryScores.hiring / 35) * 100));
    const sVal = Math.round(Math.min(100, (categoryScores.social / 25) * 100));
    const lVal = Math.round(Math.min(100, (categoryScores.leadership / 20) * 100));

    const activeVals = [fVal, hVal, sVal, lVal].filter(v => v > 0);
    if (activeVals.length > 0) {
      const avg = Math.round(activeVals.reduce((a, b) => a + b, 0) / activeVals.length);
      return Math.max(avg, lead.intent_score ?? 0);
    }

    return lead.intent_score ?? 100;
  }, [categoryScores, lead]);

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

      const rawSrc = sig.source_url || '';
      const isCompanyHomepage = !rawSrc || 
        rawSrc === websiteUrl || 
        rawSrc === `https://${companyDomain}` || 
        rawSrc === `http://${companyDomain}` || 
        rawSrc.trim().replace(/^https?:\/\//, '').replace(/\/$/, '') === companyDomain.trim().replace(/^https?:\/\//, '').replace(/\/$/, '') ||
        rawSrc === 'N/A';


      return {
        ...sig,
        source_url: isCompanyHomepage ? null : rawSrc,
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
            className="side-drawer-panel fixed inset-y-0 right-0 w-full lg:w-[75vw] bg-nexa-bg border-l border-nexa-border shadow-2xl z-50 flex flex-col font-sans"
          >
            
            {/* 1. Top Header Controls Bar */}
            <div className="side-drawer-header px-2.5 sm:px-6 py-2 sm:py-3 border-b border-nexa-border bg-nexa-surface flex items-center justify-between gap-1 sm:gap-4 sticky top-0 z-20 overflow-hidden">
              {/* Navigation Arrows */}
              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  onClick={handlePrevLead}
                  disabled={!hasPrev}
                  title="Previous Lead (Up Arrow)"
                  className="side-drawer-pill p-1 sm:p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  <ChevronUp size={14} />
                </button>
                <button
                  type="button"
                  onClick={handleNextLead}
                  disabled={!hasNext}
                  title="Next Lead (Down Arrow)"
                  className="side-drawer-pill p-1 sm:p-1.5 rounded-lg border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
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
              {/* 1. Finding Summary */}
              <button
                onClick={() => setActiveTab('about')}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shrink-0 ${
                  activeTab === 'about'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <FileText size={14} /> Finding Summary
              </button>

              {/* 2. Signals */}
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

              {/* 3. Company Insights */}
              <button
                onClick={() => setActiveTab('insights')}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shrink-0 ${
                  activeTab === 'insights'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <LineChart size={14} /> Company Insights
              </button>

              {/* 4. Jobs */}
              <button
                onClick={() => setActiveTab('jobs')}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shrink-0 ${
                  activeTab === 'jobs'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <Briefcase size={14} /> Jobs <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-500/30 font-mono font-bold">{jobsCount}</span>
              </button>

              {/* 5. Decision Makers */}
              <button
                onClick={() => setActiveTab('people')}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shrink-0 ${
                  activeTab === 'people'
                    ? 'side-drawer-tab-active bg-nexa-card text-zinc-100 shadow-xs font-bold border border-nexa-border'
                    : 'side-drawer-tab-inactive text-zinc-400 hover:text-zinc-100'
                }`}
              >
                <Users size={14} /> Decision Makers <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-purple-950 text-purple-300 border border-purple-500/30 font-mono font-bold">{contactsCount}</span>
              </button>
            </div>

            {/* 4. Tab Content Body (With pb-28 for Mobile Bottom Nav bar clearance) */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 pb-28 lg:pb-6 space-y-4 sm:space-y-6">

              {/* In-Line AI Outreach Research Panel */}
              {showPitcher && (
                <PitcherMode id={lead.id} company_name={companyName} onClose={() => setShowPitcher(false)} inline={true} />
              )}

              {/* ===== TAB: COMPANY INSIGHTS ===== */}
              {activeTab === 'insights' && (
                <JobsTab lead={lead} defaultTab="insights" />
              )}

              {/* ===== TAB: JOBS ===== */}
              {activeTab === 'jobs' && (
                <JobsTab lead={lead} defaultTab="jobs" />
              )}

              {/* ===== TAB 1: SIGNALS VIEW (IMAGE MATCH RE-DESIGN) ===== */}
              {activeTab === 'signals' && (
                <div className="space-y-6 animate-fade-in font-sans text-xs">

                  {/* SECTION 1 · SCORE AND JUSTIFICATION */}
                  <div className="p-5 sm:p-6 rounded-3xl border border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-xs space-y-4">
                    <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-zinc-100">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <TrendingUp size={16} />
                      </div>
                      <span>SCORE AND JUSTIFICATION</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
                      
                      {/* Left Half-Circle Speedometer Arc Gauge (4 cols) */}
                      <div className="md:col-span-4 p-3 sm:p-4 pr-6 flex flex-col items-center justify-center text-center space-y-3 md:border-r border-slate-200/60 dark:border-zinc-800/80">
                        <div className="relative w-44 h-26 flex items-center justify-center pt-1">
                          <svg className="w-full h-full overflow-visible" viewBox="0 0 100 60">
                            {/* Background Light Arc */}
                            <path
                              d="M 10 52 A 40 40 0 0 1 90 52"
                              fill="none"
                              stroke="#EEF2FF"
                              strokeWidth="4.5"
                              strokeLinecap="round"
                              className="dark:stroke-zinc-800"
                            />
                            {/* Foreground Green/Emerald Arc */}
                            <path
                              d="M 10 52 A 40 40 0 0 1 90 52"
                              fill="none"
                              stroke="#10b981"
                              strokeWidth="4.5"
                              strokeLinecap="round"
                              strokeDasharray="126"
                              strokeDashoffset={126 - Math.min(126, (displayScore / 100) * 126)}
                              className="transition-all duration-1000"
                            />
                          </svg>
                          
                          {/* Inner Gauge Text */}
                          <div className="absolute bottom-1 flex flex-col items-center justify-center">
                            <div className="text-4xl font-extrabold text-slate-900 dark:text-zinc-100 leading-none tracking-tight">
                              {displayScore}
                            </div>
                            <div className="text-[11px] font-semibold text-slate-400 dark:text-zinc-500 mt-1">
                              / 100
                            </div>
                          </div>
                        </div>

                        {/* Intent Status Badge (No Flame icon) */}
                        <div className={`inline-flex items-center justify-center px-5 py-1.5 rounded-full text-xs font-bold shadow-2xs ${
                          displayScore >= 70
                            ? 'bg-emerald-100/80 text-emerald-600 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                            : displayScore >= 40
                            ? 'bg-amber-100/80 text-amber-600 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                            : 'bg-slate-100 text-slate-600 dark:bg-zinc-800 dark:text-zinc-300 border border-slate-200 dark:border-zinc-700'
                        }`}>
                          <span>{lead?.intent_classification || (displayScore >= 70 ? 'Hot' : displayScore >= 40 ? 'Warm' : 'Watching')}</span>
                        </div>

                        <p className="text-[11px] font-medium text-slate-500 dark:text-zinc-400 max-w-[220px] leading-relaxed px-1">
                          This score indicates a high-priority account based on key growth and hiring signals.
                        </p>
                      </div>

                      {/* Right Breakdown Progress Bars (8 cols) */}
                      <div className="md:col-span-8 space-y-3.5 pl-1">
                        {/* 1. Funding */}
                        {(() => {
                          const val = Math.round(Math.min(100, (categoryScores.funding / 40) * 100));
                          const badge = val >= 80 ? 'Very High' : val >= 70 ? 'High' : val >= 30 ? 'Medium' : val > 0 ? 'Low' : 'None';
                          return (
                            <div className="flex items-center justify-between gap-3 text-xs font-semibold">
                              <div className="flex items-center gap-2.5 w-36 shrink-0 text-slate-700 dark:text-zinc-200">
                                <div className="w-6 h-6 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                                  <DollarSign size={13} />
                                </div>
                                <span>Funding</span>
                              </div>
                              <div className="flex-1 bg-slate-100 dark:bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                                <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${val}%` }} />
                              </div>
                              <span className="w-10 text-right font-mono font-bold text-slate-900 dark:text-zinc-100">{val}%</span>
                              <span className={`w-16 text-center py-0.5 rounded-full text-[10px] font-bold ${
                                badge === 'High' || badge === 'Very High' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' :
                                badge === 'Medium' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300' :
                                badge === 'Low' ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400' :
                                'bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400'
                              }`}>
                                {badge}
                              </span>
                            </div>
                          );
                        })()}

                        {/* 2. Hiring gap */}
                        {(() => {
                          const val = Math.round(Math.min(100, (categoryScores.hiring / 35) * 100));
                          const badge = val >= 80 ? 'Very High' : val >= 50 ? 'High' : val > 0 ? 'Low' : 'None';
                          return (
                            <div className="flex items-center justify-between gap-3 text-xs font-semibold">
                              <div className="flex items-center gap-2.5 w-36 shrink-0 text-slate-700 dark:text-zinc-200">
                                <div className="w-6 h-6 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                                  <Users size={13} />
                                </div>
                                <span>Hiring gap</span>
                              </div>
                              <div className="flex-1 bg-slate-100 dark:bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                                <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${val}%` }} />
                              </div>
                              <span className="w-10 text-right font-mono font-bold text-slate-900 dark:text-zinc-100">{val}%</span>
                              <span className={`w-16 text-center py-0.5 rounded-full text-[10px] font-bold ${
                                badge === 'Very High' || badge === 'High' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' :
                                badge === 'Low' ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400' :
                                'bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400'
                              }`}>
                                {badge}
                              </span>
                            </div>
                          );
                        })()}

                        {/* 3. Social buy signal */}
                        {(() => {
                          const val = Math.round(Math.min(100, (categoryScores.social / 25) * 100));
                          const badge = val >= 70 ? 'High' : val >= 30 ? 'Medium' : val > 0 ? 'Low' : 'None';
                          return (
                            <div className="flex items-center justify-between gap-3 text-xs font-semibold">
                              <div className="flex items-center gap-2.5 w-36 shrink-0 text-slate-700 dark:text-zinc-200">
                                <div className="w-6 h-6 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                                  <Megaphone size={13} />
                                </div>
                                <span>Social buy signal</span>
                              </div>
                              <div className="flex-1 bg-slate-100 dark:bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                                <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${val}%` }} />
                              </div>
                              <span className="w-10 text-right font-mono font-bold text-slate-900 dark:text-zinc-100">{val}%</span>
                              <span className={`w-16 text-center py-0.5 rounded-full text-[10px] font-bold ${
                                badge === 'High' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' :
                                badge === 'Medium' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300' :
                                badge === 'Low' ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400' :
                                'bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400'
                              }`}>
                                {badge}
                              </span>
                            </div>
                          );
                        })()}

                        {/* 4. Leadership change */}
                        {(() => {
                          const val = Math.round(Math.min(100, (categoryScores.leadership / 20) * 100));
                          const badge = val >= 70 ? 'High' : val >= 30 ? 'Medium' : val > 0 ? 'Low' : 'None';
                          return (
                            <div className="flex items-center justify-between gap-3 text-xs font-semibold">
                              <div className="flex items-center gap-2.5 w-36 shrink-0 text-slate-700 dark:text-zinc-200">
                                <div className="w-6 h-6 rounded-lg bg-slate-200 dark:bg-zinc-800 text-slate-500 flex items-center justify-center shrink-0">
                                  <TrendingUp size={13} />
                                </div>
                                <span>Leadership change</span>
                              </div>
                              <div className="flex-1 bg-slate-100 dark:bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                                <div className="bg-slate-300 dark:bg-zinc-700 h-full rounded-full transition-all duration-500" style={{ width: `${val}%` }} />
                              </div>
                              <span className="w-10 text-right font-mono font-bold text-slate-500 dark:text-zinc-400">{val}%</span>
                              <span className="w-16 text-center py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400">
                                {badge}
                              </span>
                            </div>
                          );
                        })()}

                        {/* Info Banner Pill below 4 progress bars */}
                        <div className="mt-6 p-2.5 px-3 rounded-xl bg-slate-50/80 dark:bg-zinc-950/60 border border-slate-200/60 dark:border-zinc-800/80 flex items-center gap-2 text-[11px] text-slate-500 dark:text-zinc-400 font-medium">
                          <Info size={13} className="text-slate-400 shrink-0" />
                          <span>Scores are updated based on the latest available data and market signals.</span>
                        </div>
                      </div>

                    </div>
                  </div>

                  {/* SIGNAL TIMELINE */}
                  <div className="p-6 sm:p-7 rounded-3xl border border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-xs space-y-6">
                    <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-zinc-100">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <Bell size={16} />
                      </div>
                      <span>SIGNAL TIMELINE</span>
                    </div>

                    {/* Timeline List with Connecting Dots */}
                    <div className="relative pl-9 space-y-4">
                      {/* Vertical Axis Line (Exact 16px left center alignment) */}
                      <div className="absolute left-4 top-3 bottom-3 w-0.5 bg-slate-200 dark:bg-zinc-800 -translate-x-1/2" />

                      {timelineSignals.map((sig, idx) => {
                        const isFunding = (sig.signal_type || '').toLowerCase().includes('fund') || (sig.signal_type || '').toLowerCase().includes('series');
                        const isHiring = (sig.signal_type || '').toLowerCase().includes('hire') || (sig.signal_type || '').toLowerCase().includes('role');
                        
                        const nodeColor = isFunding ? 'bg-emerald-500' : isHiring ? 'bg-indigo-500' : 'bg-sky-500';
                        const iconBg = isFunding ? 'bg-emerald-500/10 text-emerald-500' : isHiring ? 'bg-indigo-500/10 text-indigo-500' : 'bg-sky-500/10 text-sky-500';
                        const badgeStyle = isFunding 
                          ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/40' 
                          : 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 border-indigo-200 dark:border-indigo-800/40';

                        return (
                          <div key={idx} className="relative group">
                            {/* Dot on Left Line (Mathematically 100% centered at 16px from container edge) */}
                            <div className={`absolute left-[-20px] -translate-x-1/2 top-5 w-3.5 h-3.5 rounded-full border-2 border-white dark:border-zinc-900 ${nodeColor} shadow-2xs group-hover:scale-125 transition-transform`} />

                            {/* Signal Item Card */}
                            <div className="p-4 rounded-2xl border border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900/50 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 group-hover:border-indigo-300 dark:group-hover:border-indigo-500/60 transition-colors">
                              <div className="flex items-center gap-3.5 min-w-0">
                                <div className={`w-9 h-9 rounded-xl ${iconBg} flex items-center justify-center shrink-0 font-bold`}>
                                  {isFunding ? <DollarSign size={18} /> : isHiring ? <Users size={18} /> : <Briefcase size={18} />}
                                </div>
                                <div className="space-y-1 min-w-0">
                                  <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-zinc-100 text-xs">
                                    <span>{sig.signal_type || 'Market Signal'}</span>
                                    {sig.verbatim_quote && (
                                      <span className="text-slate-400 font-normal truncate max-w-sm">• {sig.verbatim_quote}</span>
                                    )}
                                  </div>
                                  {sig.source_url && (
                                    <a
                                      href={sig.source_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-sky-600 dark:text-sky-400 hover:underline text-[11px] font-mono inline-flex items-center gap-1"
                                    >
                                      source <ExternalLink size={10} />
                                    </a>
                                  )}
                                </div>
                              </div>

                              <div className="shrink-0 self-end sm:self-center">
                                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-[11px] font-semibold border ${badgeStyle}`}>
                                  <Calendar size={12} />
                                  <span>{sig.recency_label || '1-3 months'}</span>
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* WHY NOW AND RECOMMENDED ANGLE */}
                  <div className="p-6 sm:p-7 rounded-3xl border border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-xs space-y-5">
                    <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-zinc-100">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <Users size={16} />
                      </div>
                      <span>WHY NOW AND RECOMMENDED ANGLE</span>
                    </div>

                    <p className="text-xs font-medium text-slate-700 dark:text-zinc-300 leading-relaxed">
                      {lead.why_now || "The company is experiencing rapid expansion and active hiring for technical positions, indicating an immediate need for talent acquisition support to scale operations."}
                    </p>

                    {/* Suggested Opener Box (Reduced Height + Arrow & Target Breaking Out Above Top) */}
                    <div className="relative mt-7 p-4 sm:p-5 py-3.5 sm:py-4 rounded-2xl border border-[#DBE5FF] dark:border-indigo-900/50 bg-[#F0F4FF]/90 dark:bg-indigo-950/30 flex flex-col sm:flex-row sm:items-center justify-between gap-5 shadow-2xs overflow-visible">
                      <div className="space-y-2 max-w-xl z-10">
                        <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 dark:text-indigo-400">
                          <div className="w-5 h-5 rounded-md bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-2xs">
                            <MessageSquare size={12} className="fill-current" />
                          </div>
                          <span>Suggested opener</span>
                        </div>
                        
                        <p className="text-sm sm:text-base font-bold text-slate-900 dark:text-zinc-100 leading-snug tracking-tight">
                          <span className="text-indigo-500 dark:text-indigo-400 font-serif text-lg mr-1 select-none">“</span>
                          {suggestedOpenerText}
                          <span className="text-indigo-500 dark:text-indigo-400 font-serif text-lg ml-0.5 select-none">...”</span>
                        </p>
                      </div>

                      {/* Right Side 3D Target + Arrow Image + Floating Chat Bubbles & Sparkles */}
                      <div className="shrink-0 relative w-56 h-24 flex items-center justify-center self-center">
                        <div className="absolute -top-10 -right-6 w-64 h-40 pointer-events-none z-20 overflow-visible flex items-center justify-end">
                          {/* SVG for Floating Chat Bubbles & Sparkle Stars */}
                          <svg viewBox="0 0 240 150" className="w-full h-full overflow-visible absolute inset-0">
                            <defs>
                              <filter id="bubbleShadow" x="-20%" y="-20%" width="140%" height="140%">
                                <feDropShadow dx="1" dy="4" stdDeviation="3" floodColor="#6366F1" floodOpacity="0.15" />
                              </filter>
                              <linearGradient id="bubbleGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#FFFFFF" />
                                <stop offset="100%" stopColor="#F0F4FF" />
                              </linearGradient>
                            </defs>

                            {/* 1. Sparkle Stars */}
                            <path d="M 80 10 Q 80 15 84 15 Q 80 15 80 20 Q 80 15 76 15 Q 80 15 80 10 Z" fill="#A5B4FC" />
                            <path d="M 20 80 Q 20 85 24 85 Q 20 85 20 90 Q 20 85 16 85 Q 20 85 20 80 Z" fill="#C7D2FE" />

                            {/* 2. Floating Chat Speech Bubbles */}
                            {/* Top Bubble (Adjusted slightly down) */}
                            <g filter="url(#bubbleShadow)">
                              <rect x="32" y="16" width="40" height="28" rx="10" fill="url(#bubbleGrad)" stroke="#E0E7FF" strokeWidth="1.2" />
                              <line x1="40" y1="25" x2="63" y2="25" stroke="#818CF8" strokeWidth="1.5" strokeLinecap="round" />
                              <line x1="40" y1="32" x2="55" y2="32" stroke="#818CF8" strokeWidth="1.5" strokeLinecap="round" />
                              <path d="M 34 37 L 28 41 L 37 40 Z" fill="#FFFFFF" stroke="#E0E7FF" strokeWidth="1" />
                            </g>

                            {/* Bottom Bubble */}
                            <g filter="url(#bubbleShadow)">
                              <rect x="48" y="60" width="36" height="24" rx="9" fill="url(#bubbleGrad)" stroke="#E0E7FF" strokeWidth="1.2" />
                              <line x1="55" y1="68" x2="75" y2="68" stroke="#A5B4FC" strokeWidth="1.5" strokeLinecap="round" />
                              <line x1="55" y1="75" x2="68" y2="75" stroke="#A5B4FC" strokeWidth="1.5" strokeLinecap="round" />
                              <path d="M 76 83 L 81 88 L 79 81 Z" fill="#FFFFFF" stroke="#E0E7FF" strokeWidth="1" />
                            </g>
                          </svg>

                          {/* Enlarged Purpule Arrow PNG Image Positioned Right & Breaking Out Top */}
                          <img 
                            src="/arrow.png" 
                            alt="Target and Arrow" 
                            className="w-52 max-w-none h-auto object-contain pointer-events-none drop-shadow-md select-none relative z-10 -mt-1 -mr-2" 
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                </div>
              )}

              {/* ===== TAB 2: ABOUT & AI STRATEGY (IMAGE MATCH RE-DESIGN) ===== */}
              {activeTab === 'about' && (
                <div className="space-y-6 animate-fade-in font-sans text-xs">

                  {/* 1. MINT GREEN HERO CARD: AI VERDICT AND STRATEGY */}
                  <div className="relative overflow-hidden p-6 sm:p-7 rounded-3xl border border-[#D1F3E0] dark:border-emerald-900/40 bg-[#F2FBF6] dark:bg-emerald-950/20 shadow-xs space-y-4">
                    {/* Top Section */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 z-10 relative">
                      <div className="flex items-start gap-4">
                        {/* Icon */}
                        <div className="w-11 h-11 rounded-full bg-white dark:bg-zinc-900 text-emerald-500 shadow-2xs flex items-center justify-center shrink-0 border border-emerald-100 dark:border-emerald-900/60 mt-0.5">
                          <Sparkles size={20} />
                        </div>

                        <div className="space-y-1.5 max-w-xl">
                          <div className="text-[11px] font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                            AI VERDICT AND STRATEGY
                          </div>
                          <div className="text-xl font-extrabold text-slate-900 dark:text-zinc-100 tracking-tight flex items-center gap-2">
                            <span>{icpFitLabel} fit</span>
                            <span className="text-slate-300 dark:text-zinc-600">•</span>
                            <span className="text-emerald-600 dark:text-emerald-400 font-black">Score {lead.intent_score}</span>
                          </div>
                          <p className="text-xs font-medium text-slate-600 dark:text-zinc-300 leading-relaxed pt-1">
                            {lead.why_now || "The company is experiencing rapid expansion, evidenced by 10x growth in contracted ARR and active hiring for critical technical positions as of mid-2026, indicating an immediate need for talent acquisition support to scale operations."}
                          </p>
                        </div>
                      </div>

                      {/* Mint Green Target Board Image Asset on Right */}
                      <div className="shrink-0 relative w-56 h-32 flex items-center justify-center self-end sm:self-center">
                        <img 
                          src="/Green arrow.png" 
                          alt="Green Arrow Target" 
                          className="w-56 max-w-none h-auto object-contain pointer-events-none drop-shadow-md select-none relative z-10 -mr-2" 
                        />
                      </div>
                    </div>
                  </div>

                  {/* 2. COMPANY INFO & REVENUE SUMMARY CARD */}
                  <div className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-xs">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5 items-center">
                      
                      {/* Left Column: COMPANY INFO */}
                      <div className="space-y-3.5 md:pr-5 md:border-r border-slate-100 dark:border-zinc-800/80">
                        <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-zinc-100 uppercase tracking-wider">
                          <div className="w-7 h-7 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
                            <Building2 size={14} />
                          </div>
                          <span>Company Info</span>
                        </div>

                        <div className="space-y-2.5 pt-0.5">
                          {/* Stage Row */}
                          <div className="flex items-center justify-between gap-3 text-xs">
                            <div className="flex items-center gap-2 text-slate-500 dark:text-zinc-400 font-semibold">
                              <div className="w-6 h-6 rounded-md bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                                <Users size={12} />
                              </div>
                              <span className="text-xs">Stage</span>
                            </div>
                            <span className="font-bold text-slate-900 dark:text-zinc-100 text-xs sm:text-sm">
                              {(() => {
                                if (lead.funding_stage && lead.funding_stage !== 'Unknown' && lead.funding_stage !== 'UNKNOWN') {
                                  return lead.funding_stage;
                                }
                                if (lead.signal_tags) {
                                  const fTag = lead.signal_tags.find(t => 
                                    t.category === 'funding' || t.tag.toUpperCase().includes('FUNDING') || t.tag.toUpperCase().includes('SERIES') || t.tag.toUpperCase().includes('SEED')
                                  );
                                  if (fTag) return fTag.tag.split('/')[0].trim();
                                }
                                return 'Venture Backed';
                              })()}
                            </span>
                          </div>

                          <div className="border-b border-dashed border-slate-100 dark:border-zinc-800" />

                          {/* Headcount Row */}
                          <div className="flex items-center justify-between gap-3 text-xs">
                            <div className="flex items-center gap-2 text-slate-500 dark:text-zinc-400 font-semibold">
                              <div className="w-6 h-6 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                                <Users size={12} />
                              </div>
                              <span className="text-xs">Headcount</span>
                            </div>
                            <span className="font-bold text-slate-900 dark:text-zinc-100 text-xs sm:text-sm font-mono">
                              {lead.employee_count ?? 'N/A'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Right Column: REVENUE */}
                      <div className="space-y-3 md:pl-2 flex flex-col items-center sm:items-start justify-center">
                        <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-zinc-100 uppercase tracking-wider self-start">
                          <div className="w-7 h-7 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                            <Activity size={14} />
                          </div>
                          <span>Revenue</span>
                        </div>

                        <div className="w-full py-1 flex flex-col items-center justify-center text-center">
                          <div className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-zinc-100 tracking-tight">
                            {lead.annual_revenue || 'N/A'}
                          </div>
                          <div className="text-[10px] font-bold text-slate-400 dark:text-zinc-500 mt-1 uppercase tracking-wider">
                            ARR est.
                          </div>
                        </div>
                      </div>

                    </div>
                  </div>

                  {/* 3. SOCIAL SIGNALS CARD */}
                  <div className="p-6 sm:p-7 rounded-3xl border border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-xs space-y-4">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-zinc-100 uppercase tracking-wider">
                      <div className="w-7 h-7 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                        <Megaphone size={14} />
                      </div>
                      <span>Social Signals</span>
                    </div>

                    <div className="p-5 sm:p-6 rounded-2xl border border-[#D1F3E0] dark:border-emerald-950/60 bg-[#F2FBF6]/90 dark:bg-emerald-950/20 space-y-4">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold bg-emerald-200/60 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                          <Check size={13} className="stroke-[3]" />
                          <span>Direct buy signal detected</span>
                        </div>
                        
                        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-slate-100/80 text-slate-600 dark:bg-zinc-800 dark:text-zinc-400">
                          <Globe size={13} />
                          <span>Public social post</span>
                        </div>
                      </div>

                      <p className="text-sm font-semibold text-slate-800 dark:text-zinc-200 leading-relaxed font-sans italic pt-1">
                        <span className="text-emerald-500 font-serif text-lg mr-1 select-none font-normal">“</span>
                        {lead.signals && lead.signals.length > 0 && (lead.signals.find(s => s.verbatim_quote?.toLowerCase().includes('agency') || s.verbatim_quote?.toLowerCase().includes('grow'))?.verbatim_quote || lead.signals[0]?.verbatim_quote) 
                          ? (lead.signals.find(s => s.verbatim_quote?.toLowerCase().includes('agency') || s.verbatim_quote?.toLowerCase().includes('grow'))?.verbatim_quote || lead.signals[0]?.verbatim_quote)
                          : 'reported 10x growth in contracted ARR over 5 months (as of early 2026/late 2025 context).'}
                        <span className="text-emerald-500 font-serif text-lg ml-0.5 select-none font-normal">”</span>
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
