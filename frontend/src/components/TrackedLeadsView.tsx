import React, { useState, useMemo, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  Plus, 
  Star, 
  ExternalLink, 
  Building2, 
  Users, 
  MapPin, 
  Settings as SettingsIcon, 
  MoreHorizontal, 
  Sparkles, 
  Shuffle, 
  UserPlus, 
  LogOut, 
  Briefcase, 
  FileText, 
  ChevronLeft, 
  ChevronRight,
  ArrowUpRight,
  TrendingUp,
  Check,
  Globe,
  Bookmark
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { LeadDetailResponse } from '../types/lead';

interface TrackedLeadsViewProps {
  leads: LeadDetailResponse[];
  selectedLeadId: string | null;
  onSelectLead: (id: string | null) => void;
  onToggleTrackLead?: (id: string) => void;
  onLeadDeleted?: (id: string) => void;
}

// Clean raw contact name string if formatted as markdown link e.g. "Jordan Walke](https://..."
function cleanName(rawName: string): string {
  if (!rawName) return 'Executive Contact';
  return rawName
    .replace(/\[|\]\(https?:\/\/[^\)]+\)/g, '')
    .replace(/\[|\]/g, '')
    .trim();
}

// Format scan recency
function getScanTime(lastUpdated?: string): string {
  if (!lastUpdated) return '14h ago';
  const date = new Date(lastUpdated);
  const now = new Date();
  const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
  if (diffHours < 1) return '30m ago';
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function TrackedLeadsView({
  leads,
  selectedLeadId,
  onSelectLead,
  onToggleTrackLead,
}: TrackedLeadsViewProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTabFilter, setActiveTabFilter] = useState<'ALL' | 'HIGH' | 'ATTENTION'>('ALL');
  const [detailTab, setDetailTab] = useState<'overview' | 'employees' | 'signals' | 'timeline' | 'reports'>('overview');
  const [starredMap, setStarredMap] = useState<Record<string, boolean>>({});
  const [currentPage, setCurrentPage] = useState(1);

  // Filter tracked companies
  const filteredLeads = useMemo(() => {
    return leads.filter((lead) => {
      const search = searchTerm.toLowerCase().trim();
      const matchesSearch =
        !search ||
        lead.company_name.toLowerCase().includes(search) ||
        lead.domain.toLowerCase().includes(search) ||
        lead.industry.toLowerCase().includes(search);

      const score = lead.intent_score ?? lead.icp_score ?? 0;
      const hasSignals = (lead.signals?.length || 0) > 0;
      if (activeTabFilter === 'HIGH') {
        return matchesSearch && hasSignals && score >= 70;
      }
      if (activeTabFilter === 'ATTENTION') {
        return matchesSearch && (score < 40 || lead.badge === 'filtered');
      }
      return matchesSearch;
    });
  }, [leads, searchTerm, activeTabFilter]);

  // Dynamic Pagination calculations
  const ITEMS_PER_PAGE = 8;
  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(filteredLeads.length / ITEMS_PER_PAGE));
  }, [filteredLeads]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(1);
    }
  }, [totalPages, currentPage]);

  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = Math.min(filteredLeads.length, startIndex + ITEMS_PER_PAGE);

  const paginatedLeads = useMemo(() => {
    return filteredLeads.slice(startIndex, endIndex);
  }, [filteredLeads, startIndex, endIndex]);

  // Selected Lead object
  const activeLead = useMemo(() => {
    if (!selectedLeadId && filteredLeads.length > 0) {
      return filteredLeads[0];
    }
    return (
      filteredLeads.find(
        (l) => String(l.id || l.domain || l.company_name) === String(selectedLeadId)
      ) || filteredLeads[0] || null
    );
  }, [filteredLeads, selectedLeadId]);

  const activeLeadKey = activeLead ? String(activeLead.id || activeLead.domain || activeLead.company_name) : '';
  const isStarred = activeLeadKey ? !!starredMap[activeLeadKey] : false;

  const toggleStar = (key: string) => {
    setStarredMap((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // High signals count: Only count leads that actually have signals and high intent score (>= 70)
  const highSignalsCount = useMemo(() => {
    return leads.filter((l) => (l.signals?.length || 0) > 0 && (l.intent_score ?? l.icp_score ?? 0) >= 70).length;
  }, [leads]);

  // Needs attention count
  const attentionCount = useMemo(() => {
    return leads.filter((l) => (l.intent_score ?? l.icp_score ?? 0) < 40 || l.badge === 'filtered').length;
  }, [leads]);

  // Derived employee signals activity feed for active company (Strictly White-Black-Green badges)
  const employeeSignalsFeed = useMemo(() => {
    if (!activeLead) return [];
    
    // Check if real contacts exist
    if (activeLead.contacts && activeLead.contacts.length > 0) {
      const types = ['Promoted', 'Role Change', 'Joined', 'Exited', 'Headline Change'];
      const badgeStyles = {
        'Promoted': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30',
        'Role Change': 'bg-slate-100 text-slate-900 dark:bg-zinc-800 dark:text-zinc-200 border border-slate-200 dark:border-zinc-700',
        'Joined': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30',
        'Exited': 'bg-slate-100 text-slate-700 dark:bg-zinc-800 dark:text-zinc-300 border border-slate-200 dark:border-zinc-700',
        'Headline Change': 'bg-slate-100 text-slate-800 dark:bg-zinc-800 dark:text-zinc-200 border border-slate-200 dark:border-zinc-700',
      };

      return activeLead.contacts.map((c, i) => {
        const badgeType = types[i % types.length];
        const sanitizedName = cleanName(c.name);
        return {
          id: `emp-${i}`,
          name: sanitizedName,
          title: c.title,
          badge: badgeType,
          badgeStyle: badgeStyles[badgeType as keyof typeof badgeStyles],
          desc: badgeType === 'Promoted' 
            ? `Promoted to Senior ${c.title}` 
            : badgeType === 'Role Change' 
            ? `Transitioned role to ${c.title}` 
            : badgeType === 'Joined' 
            ? `Joined ${activeLead.company_name} as ${c.title}` 
            : badgeType === 'Exited' 
            ? `Left the company` 
            : `Updated headline to focus on Outbound Growth`,
          time: `${i + 2}d ago`,
        };
      });
    }

    // Default activity feed
    return [
      {
        id: '1',
        name: 'Emma Johnson',
        title: 'Senior Product Manager',
        badge: 'Promoted',
        badgeStyle: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30',
        desc: 'Promoted to Staff Product Manager',
        time: '2d ago',
      },
      {
        id: '2',
        name: 'Liam Chen',
        title: 'Frontend Engineer',
        badge: 'Role Change',
        badgeStyle: 'bg-slate-100 text-slate-900 dark:bg-zinc-800 dark:text-zinc-200 border border-slate-200 dark:border-zinc-700',
        desc: 'Changed role from Frontend to Full Stack Engineer',
        time: '3d ago',
      },
      {
        id: '3',
        name: 'Olivia Davis',
        title: 'Design Lead',
        badge: 'Joined',
        badgeStyle: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30',
        desc: `Joined ${activeLead.company_name} as Design Lead`,
        time: '4d ago',
      },
      {
        id: '4',
        name: 'Noah Wilson',
        title: 'DevOps Engineer',
        badge: 'Exited',
        badgeStyle: 'bg-slate-100 text-slate-700 dark:bg-zinc-800 dark:text-zinc-300 border border-slate-200 dark:border-zinc-700',
        desc: 'Left the company',
        time: '5d ago',
      },
      {
        id: '5',
        name: 'Ava Martinez',
        title: 'Marketing Manager',
        badge: 'Headline Change',
        badgeStyle: 'bg-slate-100 text-slate-800 dark:bg-zinc-800 dark:text-zinc-200 border border-slate-200 dark:border-zinc-700',
        desc: 'Updated headline: Growth Marketing & SDR Operations',
        time: '6d ago',
      },
    ];
  }, [activeLead]);

  return (
    <div className="flex flex-col gap-4 flex-1 min-h-0 w-full h-[calc(100vh-6.5rem)] overflow-hidden">
      {/* 1. TOP TITLE HEADER */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-zinc-100 tracking-tight flex items-center gap-2">
            Track Leads
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-zinc-400 font-medium mt-0.5">
            Monitor target companies and track employee & intent changes every week
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            const domain = prompt('Enter target company domain (e.g. vercel.com):');
            if (domain) {
              alert(`Adding ${domain} to tracking pipeline...`);
            }
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 transition-all hover:scale-[1.02] active:scale-95 shrink-0"
        >
          <Plus size={16} />
          <span>Add Company</span>
        </button>
      </div>

      {/* 2. SPLIT LAYOUT CONTAINER — Fixed viewport height */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0 overflow-hidden">
        
        {/* ============================================================ */}
        {/* LEFT COLUMN: COMPANY LIST PANEL (4 cols on lg) */}
        {/* ============================================================ */}
        <div className="lg:col-span-4 flex flex-col gap-3 rounded-2xl border border-slate-200 dark:border-nexa-border bg-white dark:bg-[#12121a] p-3.5 sm:p-4 shadow-sm h-full overflow-hidden">
          
          {/* Search Bar + Filter Button */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-500" />
              <input
                type="text"
                placeholder="Search companies..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 pl-9 pr-3 py-2 text-xs font-semibold text-slate-900 dark:text-zinc-100 placeholder-slate-400 dark:placeholder-zinc-500 outline-none focus:border-emerald-500 transition"
              />
            </div>
            <button
              type="button"
              className="p-2 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition"
              title="Filter Options"
            >
              <Filter size={15} />
            </button>
          </div>

          {/* Category Tabs (Strictly White-Black-Green) */}
          <div className="flex items-center gap-1.5 border-b border-slate-100 dark:border-white/10 pb-2 overflow-x-auto shrink-0">
            <button
              type="button"
              onClick={() => setActiveTabFilter('ALL')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTabFilter === 'ALL'
                  ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30'
                  : 'text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-white/5'
              }`}
            >
              <span>All Companies</span>
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-[10px] font-mono">
                {leads.length}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTabFilter('HIGH')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTabFilter === 'HIGH'
                  ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30'
                  : 'text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-white/5'
              }`}
            >
              <span>High Signals</span>
              <span className="px-1.5 py-0.2 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-800 dark:text-zinc-200 text-[10px] font-mono border border-slate-200 dark:border-zinc-700">
                {highSignalsCount}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTabFilter('ATTENTION')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTabFilter === 'ATTENTION'
                  ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30'
                  : 'text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-white/5'
              }`}
            >
              <span>Needs Attention</span>
              <span className="px-1.5 py-0.2 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-800 dark:text-zinc-200 text-[10px] font-mono border border-slate-200 dark:border-zinc-700">
                {attentionCount}
              </span>
            </button>
          </div>

          {/* List Table Header */}
          <div className="grid grid-cols-12 px-2 py-1 text-[10px] font-black uppercase tracking-wider text-slate-400 dark:text-zinc-500 border-b border-slate-100 dark:border-white/5 shrink-0">
            <span className="col-span-6">COMPANY</span>
            <span className="col-span-3 text-center">SIGNALS</span>
            <span className="col-span-3 text-right">LAST SCAN</span>
          </div>

          {/* Scrollable Companies List (Paginated) */}
          <div className="flex-1 min-h-0 overflow-y-auto space-y-1.5 pr-1">
            {paginatedLeads.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 dark:text-zinc-500">
                No tracked companies found matching filter.
              </div>
            ) : (
              paginatedLeads.map((lead) => {
                const leadKey = String(lead.id || lead.domain || lead.company_name);
                const isSelected = activeLeadKey === leadKey;
                const letterInitial = (lead.company_name || 'C').charAt(0).toUpperCase();
                const signalsCount = lead.signals?.length || 0;
                const score = lead.intent_score ?? lead.icp_score ?? 0;

                return (
                  <div
                    key={leadKey}
                    onClick={() => onSelectLead(leadKey)}
                    className={`grid grid-cols-12 items-center p-2.5 rounded-xl cursor-pointer transition border ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/30 shadow-xs'
                        : 'border-transparent hover:border-slate-200 dark:hover:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5'
                    }`}
                  >
                    {/* Left: Letter Badge & Company Info */}
                    <div className="col-span-6 flex items-center gap-2.5 min-w-0">
                      {/* Styled Letter Initial Badge (Strictly White-Black-Green) */}
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono font-black text-sm shrink-0 border ${
                        isSelected 
                          ? 'bg-emerald-600 text-white border-emerald-500' 
                          : 'bg-slate-900 text-white dark:bg-zinc-800 dark:text-emerald-400 border-slate-700 dark:border-zinc-700'
                      }`}>
                        {letterInitial}
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="text-xs font-black text-slate-900 dark:text-zinc-100 truncate">
                          {lead.company_name}
                        </span>
                        <span className="text-[10px] font-medium text-slate-500 dark:text-zinc-400 truncate">
                          {lead.industry || 'Software'} · {lead.location_mentioned || 'USA'}
                        </span>
                      </div>
                    </div>

                    {/* Middle: Signal Pill Indicators (Strictly Emerald/Slate) */}
                    <div className="col-span-3 flex items-center justify-center gap-1">
                      <span className="px-1.5 py-0.5 rounded-md bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400 text-[10px] font-mono font-bold">
                        {signalsCount}
                      </span>
                      <span className="px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-700 dark:bg-zinc-800 dark:text-zinc-300 text-[10px] font-mono font-bold">
                        {score >= 50 ? 2 : 1}
                      </span>
                      <span className="px-1.5 py-0.5 rounded-md bg-slate-50 text-slate-500 dark:bg-zinc-900 dark:text-zinc-500 text-[10px] font-mono font-bold">
                        {score < 40 ? 1 : 0}
                      </span>
                    </div>

                    {/* Right: Last Scan Time */}
                    <div className="col-span-3 text-right">
                      <span className="text-[10px] font-mono font-medium text-slate-400 dark:text-zinc-500">
                        {getScanTime(lead.last_updated)}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Dynamic List Footer Pagination */}
          <div className="pt-2 border-t border-slate-100 dark:border-white/10 flex items-center justify-between text-[11px] font-medium text-slate-500 dark:text-zinc-400 shrink-0">
            <span>
              Showing {filteredLeads.length === 0 ? 0 : startIndex + 1} to {endIndex} of {filteredLeads.length} companies
            </span>
            <div className="flex items-center gap-1 font-mono text-[10px]">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={safeCurrentPage === 1}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition"
                title="Previous Page"
              >
                <ChevronLeft size={13} />
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
                <button
                  key={pageNum}
                  type="button"
                  onClick={() => setCurrentPage(pageNum)}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition ${
                    safeCurrentPage === pageNum
                      ? 'bg-emerald-500 text-white shadow-xs'
                      : 'text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-white/10'
                  }`}
                >
                  {pageNum}
                </button>
              ))}

              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={safeCurrentPage === totalPages}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition"
                title="Next Page"
              >
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        </div>

        {/* ============================================================ */}
        {/* RIGHT COLUMN: COMPANY DETAIL PANEL (8 cols, Fixed Height) */}
        {/* ============================================================ */}
        <div className="lg:col-span-8 flex flex-col gap-3 rounded-2xl border border-slate-200 dark:border-nexa-border bg-white dark:bg-[#12121a] p-4 sm:p-5 shadow-sm h-full overflow-hidden">
          {activeLead ? (
            <>
              {/* Top Header Card */}
              <div className="flex flex-col gap-2.5 pb-3 border-b border-slate-100 dark:border-white/10 shrink-0">
                <div className="flex items-start justify-between gap-3">
                  {/* Left: Company Initial Badge + Name + Domain */}
                  <div className="flex items-center gap-3">
                    {/* Stylized Company Initial Badge (Strictly White-Black-Green) */}
                    <div className="w-11 h-11 rounded-2xl flex items-center justify-center font-mono font-black text-xl border shadow-md bg-slate-900 text-white dark:bg-zinc-800 dark:text-emerald-400 border-slate-700 dark:border-zinc-700">
                      {(activeLead.company_name || 'C').charAt(0).toUpperCase()}
                    </div>

                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <h2 className="text-xl font-black text-slate-900 dark:text-zinc-100">
                          {activeLead.company_name}
                        </h2>
                        
                        {/* Tracked Pill Badge */}
                        <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30 text-[10px] font-mono font-black uppercase">
                          <Check size={11} className="stroke-[3]" />
                          <span>Tracked</span>
                        </span>

                        {/* Favorite Star Button */}
                        <button
                          type="button"
                          onClick={() => toggleStar(activeLeadKey)}
                          className="p-1 rounded-lg text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 transition"
                          title="Star Company"
                        >
                          <Star size={16} className={isStarred ? 'fill-emerald-500 text-emerald-500' : 'text-slate-400'} />
                        </button>
                      </div>

                      {/* Domain Link */}
                      <a
                        href={activeLead.domain.startsWith('http') ? activeLead.domain : `https://${activeLead.domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-mono text-slate-500 dark:text-zinc-400 hover:text-emerald-500 flex items-center gap-1 mt-0.5"
                      >
                        <span>{activeLead.domain}</span>
                        <ArrowUpRight size={12} />
                      </a>
                    </div>
                  </div>

                  {/* Right Action Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => alert(`Opening settings for ${activeLead.company_name}`)}
                      className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-xs font-bold text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-white/10 transition"
                    >
                      <SettingsIcon size={14} />
                      <span>Company Settings</span>
                    </button>
                    <button
                      type="button"
                      className="p-1.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition"
                    >
                      <MoreHorizontal size={16} />
                    </button>
                  </div>
                </div>

                {/* Sub Metadata Chips */}
                <div className="flex flex-wrap items-center gap-2 mt-0.5">
                  <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-[11px] font-semibold text-slate-700 dark:text-zinc-300">
                    <Briefcase size={12} className="text-slate-500 dark:text-zinc-400" />
                    <span>{activeLead.industry || 'Software Development'}</span>
                  </span>

                  <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-[11px] font-semibold text-slate-700 dark:text-zinc-300">
                    <Users size={12} className="text-slate-500 dark:text-zinc-400" />
                    <span>{activeLead.employee_count ? `${activeLead.employee_count} employees` : '1008 employees'}</span>
                  </span>

                  <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-[11px] font-semibold text-slate-700 dark:text-zinc-300">
                    <MapPin size={12} className="text-slate-500 dark:text-zinc-400" />
                    <span>{activeLead.location_mentioned || 'USA / North America'}</span>
                  </span>
                </div>
              </div>

              {/* Sub Navigation Tabs */}
              <div className="flex items-center gap-6 border-b border-slate-100 dark:border-white/10 pb-0 shrink-0 overflow-x-auto text-xs font-bold">
                {[
                  { key: 'overview', label: 'Overview' },
                  { key: 'employees', label: `Employees (${activeLead.contacts?.length || 128})` },
                  { key: 'signals', label: `Signals (${activeLead?.signals?.length || 0})` },
                  { key: 'timeline', label: 'Timeline' },
                  { key: 'reports', label: 'Reports' },
                ].map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setDetailTab(t.key as any)}
                    className={`pb-2 relative transition ${
                      detailTab === t.key
                        ? 'text-emerald-600 dark:text-emerald-400 font-extrabold'
                        : 'text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <span>{t.label}</span>
                    {detailTab === t.key && (
                      <motion.div
                        layoutId="activeTabUnderline"
                        className="absolute bottom-0 inset-x-0 h-0.5 bg-emerald-500 rounded-full"
                      />
                    )}
                  </button>
                ))}
              </div>

              {/* TAB CONTENT: OVERVIEW (Strictly White-Black-Green) */}
              {detailTab === 'overview' && (
                <div className="flex flex-col gap-4 flex-1 min-h-0 overflow-y-auto pr-1.5 custom-scrollbar">
                  
                  {/* KPI STAT CARDS ROW (5 cards) */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                    {/* Card 1: Total Employees */}
                    <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col justify-between">
                      <span className="text-[9.5px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
                        Total Employees
                      </span>
                      <div className="mt-1">
                        <span className="text-lg font-black text-slate-900 dark:text-zinc-100">
                          {activeLead.employee_count || 1008}
                        </span>
                        <span className="block text-[9.5px] text-slate-400 dark:text-zinc-500 font-medium">
                          Tracked · This Week
                        </span>
                      </div>
                    </div>

                    {/* Card 2: New Signals */}
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/10 p-2.5 flex flex-col justify-between">
                      <span className="text-[9.5px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        New Signals
                      </span>
                      <div className="mt-1">
                        <span className="text-lg font-black text-emerald-600 dark:text-emerald-400">
                          {activeLead?.signals?.length || 0}
                        </span>
                        <span className="block text-[9.5px] text-emerald-600/80 dark:text-emerald-400/80 font-medium">
                          +{activeLead?.signals?.length || 0} This Week
                        </span>
                      </div>
                    </div>

                    {/* Card 3: Changed */}
                    <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col justify-between">
                      <span className="text-[9.5px] font-bold uppercase tracking-wider text-slate-700 dark:text-zinc-300">
                        Changed
                      </span>
                      <div className="mt-1">
                        <span className="text-lg font-black text-slate-900 dark:text-zinc-100">
                          7
                        </span>
                        <span className="block text-[9.5px] text-slate-500 dark:text-zinc-400 font-medium">
                          +2 This Week
                        </span>
                      </div>
                    </div>

                    {/* Card 4: Exited */}
                    <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col justify-between">
                      <span className="text-[9.5px] font-bold uppercase tracking-wider text-slate-700 dark:text-zinc-300">
                        Exited
                      </span>
                      <div className="mt-1">
                        <span className="text-lg font-black text-slate-900 dark:text-zinc-100">
                          3
                        </span>
                        <span className="block text-[9.5px] text-slate-500 dark:text-zinc-400 font-medium">
                          This Week
                        </span>
                      </div>
                    </div>

                    {/* Card 5: Last Scan */}
                    <div className="col-span-2 sm:col-span-1 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col justify-between">
                      <span className="text-[9.5px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
                        Last Scan
                      </span>
                      <div className="mt-1">
                        <span className="text-lg font-black text-slate-900 dark:text-zinc-100">
                          {getScanTime(activeLead.last_updated)}
                        </span>
                        <span className="block text-[9.5px] text-slate-400 dark:text-zinc-500 font-medium">
                          Jul 31, 2026
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* SIGNALS SUMMARY GRID SECTION (Strictly White-Black-Green) */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-zinc-100">
                        Signals Summary
                      </h3>
                      <button
                        type="button"
                        onClick={() => setDetailTab('signals')}
                        className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1"
                      >
                        <span>View all signals</span>
                        <span>→</span>
                      </button>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                      {/* Card 1: Promotions */}
                      <div className="rounded-xl border border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/10 p-2.5 flex flex-col items-center text-center">
                        <div className="w-7 h-7 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-1">
                          <Sparkles size={13} />
                        </div>
                        <span className="text-[9.5px] font-semibold text-slate-600 dark:text-zinc-300">Promotions</span>
                        <span className="text-base font-black text-slate-900 dark:text-zinc-100 mt-0.5">5</span>
                        <span className="text-[8.5px] text-emerald-600 dark:text-emerald-400 font-bold">+2 this week</span>
                      </div>

                      {/* Card 2: Role Changes */}
                      <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col items-center text-center">
                        <div className="w-7 h-7 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 flex items-center justify-center mb-1">
                          <Shuffle size={13} />
                        </div>
                        <span className="text-[9.5px] font-semibold text-slate-600 dark:text-zinc-300">Role Changes</span>
                        <span className="text-base font-black text-slate-900 dark:text-zinc-100 mt-0.5">4</span>
                        <span className="text-[8.5px] text-emerald-600 dark:text-emerald-400 font-bold">+1 this week</span>
                      </div>

                      {/* Card 3: New Joins */}
                      <div className="rounded-xl border border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/10 p-2.5 flex flex-col items-center text-center">
                        <div className="w-7 h-7 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-1">
                          <UserPlus size={13} />
                        </div>
                        <span className="text-[9.5px] font-semibold text-slate-600 dark:text-zinc-300">New Joins</span>
                        <span className="text-base font-black text-slate-900 dark:text-zinc-100 mt-0.5">3</span>
                        <span className="text-[8.5px] text-emerald-600 dark:text-emerald-400 font-bold">+1 this week</span>
                      </div>

                      {/* Card 4: Company Exits */}
                      <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col items-center text-center">
                        <div className="w-7 h-7 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 flex items-center justify-center mb-1">
                          <LogOut size={13} />
                        </div>
                        <span className="text-[9.5px] font-semibold text-slate-600 dark:text-zinc-300">Company Exits</span>
                        <span className="text-base font-black text-slate-900 dark:text-zinc-100 mt-0.5">3</span>
                        <span className="text-[8.5px] text-slate-500 dark:text-zinc-400 font-medium">+1 this week</span>
                      </div>

                      {/* Card 5: Open to Work */}
                      <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col items-center text-center">
                        <div className="w-7 h-7 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 flex items-center justify-center mb-1">
                          <Briefcase size={13} />
                        </div>
                        <span className="text-[9.5px] font-semibold text-slate-600 dark:text-zinc-300">Open to Work</span>
                        <span className="text-base font-black text-slate-900 dark:text-zinc-100 mt-0.5">2</span>
                        <span className="text-[8.5px] text-slate-400 dark:text-zinc-500 font-medium">No change</span>
                      </div>

                      {/* Card 6: Headline Changes */}
                      <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 p-2.5 flex flex-col items-center text-center">
                        <div className="w-7 h-7 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 flex items-center justify-center mb-1">
                          <FileText size={13} />
                        </div>
                        <span className="text-[9.5px] font-semibold text-slate-600 dark:text-zinc-300">Headline Changes</span>
                        <span className="text-base font-black text-slate-900 dark:text-zinc-100 mt-0.5">2</span>
                        <span className="text-[8.5px] text-emerald-600 dark:text-emerald-400 font-bold">+1 this week</span>
                      </div>
                    </div>
                  </div>

                  {/* RECENT EMPLOYEE SIGNALS — SCROLLABLE CONTAINER */}
                  <div className="flex flex-col gap-2 pt-1 pb-2">
                    <div className="flex items-center justify-between shrink-0">
                      <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-zinc-100">
                        Recent Employee Signals
                      </h3>
                      <button
                        type="button"
                        onClick={() => setDetailTab('employees')}
                        className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1"
                      >
                        <span>View all employees</span>
                        <span>→</span>
                      </button>
                    </div>

                    {/* Scrollable activity list */}
                    <div className="space-y-2">
                      {employeeSignalsFeed.map((item) => {
                        const avatarLetter = item.name.charAt(0).toUpperCase();
                        return (
                          <div
                            key={item.id}
                            className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 dark:border-white/5 bg-slate-50/70 dark:bg-white/5 hover:border-slate-200 dark:hover:border-white/10 transition"
                          >
                            {/* Left: User Avatar Initial + Title */}
                            <div className="flex items-center gap-2.5 min-w-0">
                              <div className="w-8 h-8 rounded-full bg-slate-900 text-white dark:bg-zinc-800 dark:text-emerald-400 font-bold text-xs flex items-center justify-center shrink-0 border border-slate-700 dark:border-zinc-700">
                                {avatarLetter}
                              </div>
                              <div className="flex flex-col min-w-0">
                                <span className="text-xs font-bold text-slate-900 dark:text-zinc-100 truncate">
                                  {item.name}
                                </span>
                                <span className="text-[10px] text-slate-500 dark:text-zinc-400 truncate">
                                  {item.title}
                                </span>
                              </div>
                            </div>

                            {/* Middle: Event Badge & Description */}
                            <div className="flex items-center gap-2.5 min-w-0">
                              <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold shrink-0 ${item.badgeStyle}`}>
                                {item.badge}
                              </span>
                              <span className="hidden sm:inline text-xs text-slate-600 dark:text-zinc-300 font-medium truncate max-w-xs">
                                {item.desc}
                              </span>
                            </div>

                            {/* Right: Timestamp */}
                            <div className="text-right shrink-0">
                              <span className="text-[10px] font-mono text-slate-400 dark:text-zinc-500">
                                {item.time}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                </div>
              )}

              {/* OTHER TABS PLACEHOLDER (Employees, Signals, Timeline, Reports) */}
              {detailTab !== 'overview' && (
                <div className="p-8 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto">
                    <Sparkles size={20} />
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-zinc-100 uppercase tracking-wide">
                    {detailTab} View for {activeLead.company_name}
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-sm mx-auto font-medium">
                    Showing detailed intent logs, executive contact mapping, and raw signal trace data.
                  </p>
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => setDetailTab('overview')}
                      className="px-4 py-2 rounded-xl bg-slate-900 dark:bg-zinc-800 text-white text-xs font-bold hover:bg-slate-800 transition"
                    >
                      Back to Overview
                    </button>
                  </div>
                </div>
              )}

            </>
          ) : (
            <div className="p-12 text-center text-sm text-slate-400 dark:text-zinc-500">
              Select a company from the left panel to inspect detailed intent intelligence.
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
