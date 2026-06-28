import { ChevronDown, MailPlus, Trash2, Loader2, Search, Filter, Check, X } from 'lucide-react';
import { Fragment, useMemo, useState } from 'react';
import type { LeadDetailResponse, LeadTier } from '../types/lead';
import ConfidenceMeter from './ConfidenceMeter';
import PitcherMode from './PitcherMode';
import ScoreBreakdown from './ScoreBreakdown';
import HackerScanAnimation from './HackerScanAnimation';
import { ingestLead, deleteLead } from '../lib/api';

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

function badgeLabel(badge: LeadDetailResponse['badge']) {
  if (badge === 'new_today') return 'New Today';
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
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

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
              placeholder="Search..."
              type="text"
              value={searchTerm}
            />
          </div>
          <button
            className="flex h-[32px] items-center gap-2 whitespace-nowrap rounded-xl border border-white/5 bg-white/5 px-4 text-xs text-zinc-300 transition hover:bg-white/10 hover:text-zinc-100"
            type="button"
          >
            <Filter size={14} aria-hidden="true" />
            Filter
          </button>
          <button
            className="flex h-[32px] items-center gap-2 whitespace-nowrap rounded-lg border border-[var(--nexa-accent)]/30 bg-[var(--nexa-accent-dim)] px-4 text-xs font-semibold text-[var(--nexa-accent)] transition hover:bg-[var(--nexa-accent-glow)] disabled:opacity-50"
            onClick={handleScan}
            disabled={isScanning || !searchTerm.trim()}
          >
            {isScanning ? <Loader2 size={14} className="animate-spin" /> : null}
            Scan
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
              {tier === 'ALL' ? 'All' : tier}
            </button>
          ))}
        </div>
      </div>

      {/* Data Grid Card */}
      <div className="nexa-card overflow-hidden flex-1 flex flex-col min-h-0 relative">
        {isScanning && <HackerScanAnimation targetDomain={searchTerm} />}
        
        <div className="overflow-x-auto flex-1">
        <table className="w-full min-w-[900px] border-collapse text-left">
          <thead>
            <tr className="border-b border-nexa-border text-[10px] font-semibold uppercase tracking-wider text-zinc-600">
              <th className="p-4">Company</th>
              <th className="p-4">Activity Alert</th>
              <th className="p-4">Intent Score</th>
              <th className="p-4">ICP Fit</th>
              <th className="p-4">Why Now</th>
              <th className="p-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {filteredLeads.map((lead) => (
              <Fragment key={lead.id}>
                <tr className="nexa-row-hover border-b border-nexa-border">
                  {/* Company */}
                  <td className="p-4 font-medium text-zinc-100">
                    <button
                      className="flex items-center gap-3 text-left"
                      onClick={() =>
                        onSelectLead(selectedLeadId === lead.id ? null : lead.id)
                      }
                      type="button"
                    >
                      <ChevronDown
                        className={`text-zinc-600 transition ${
                          selectedLeadId === lead.id ? 'rotate-180 text-[var(--nexa-accent)]' : ''
                        }`}
                        size={15}
                        aria-hidden="true"
                      />
                      <span className="flex flex-col items-start gap-0.5">
                        <span className="flex items-center gap-2">
                          {lead.company_name}
                          <span
                            className={`rounded border px-1.5 py-0 text-[9px] font-semibold uppercase ${tierClass(
                              lead.tier
                            )}`}
                          >
                            {lead.tier}
                          </span>
                        </span>
                        <span className="flex items-center gap-2 font-mono text-[11px] text-zinc-600">
                          <span>{lead.domain}</span>
                          {lead.employee_count && (
                            <span 
                              className="rounded bg-white/5 px-1.5 py-0.5 text-[9px] text-zinc-500" 
                              title="Employee Count"
                            >
                              {lead.employee_count.toLocaleString()} emp
                            </span>
                          )}
                        </span>
                      </span>
                    </button>
                  </td>
                  {/* Activity Alert Badge */}
                  <td className="p-4">
                    {badgeLabel(lead.badge) ? (
                      <span
                        className={`inline-block rounded border px-2 py-0.5 font-mono text-[11px] ${badgeClass(
                          lead.badge
                        )}`}
                      >
                        {badgeLabel(lead.badge)}
                      </span>
                    ) : (
                      <span className="text-[11px] text-zinc-700">—</span>
                    )}
                  </td>
                  {/* Intent Score Bar */}
                  <td className="p-4">
                    {(() => {
                      const displayScore = (lead.badge === 'filtered' || lead.ai_verdict?.includes('API Error')) ? 0 : lead.intent_score;
                      return (
                        <div className="flex items-center gap-2.5">
                          <div className="h-2 w-20 overflow-hidden rounded-full bg-nexa-surface">
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
                          <span className="font-mono text-xs font-bold text-zinc-300">
                            {displayScore}
                          </span>
                        </div>
                      );
                    })()}
                  </td>
                  {/* ICP Fit */}
                  <td className="p-4">
                    <span
                      className={`rounded border px-2 py-0.5 text-[11px] font-medium ${icpClass(
                        lead.icp_fit
                      )}`}
                    >
                      {lead.icp_fit} Fit
                    </span>
                  </td>
                  {/* Tier column removed */}
                  {/* Operational Context (why_now) */}
                  <td
                    className="max-w-[220px] truncate p-4 text-xs text-zinc-500"
                    title={lead.why_now}
                  >
                    {lead.why_now}
                  </td>
                  {/* Actions */}
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-1.5">
                      <button
                        aria-label={`Open Pitcher Mode for ${lead.company_name}`}
                        className="inline-flex items-center justify-center rounded-md border border-nexa-border bg-nexa-surface p-2 text-zinc-400 transition hover:border-[var(--nexa-accent)]/50 hover:text-[var(--nexa-accent)]"
                        onClick={() => setPitcherLead(lead)}
                        type="button"
                      >
                        <MailPlus size={14} aria-hidden="true" />
                      </button>
                      
                      {confirmDeleteId === lead.id ? (
                        <>
                          <button
                            aria-label={`Confirm delete for ${lead.company_name}`}
                            className="inline-flex items-center justify-center rounded-md border border-rose-500/50 bg-[var(--nexa-rose-dim)] p-2 text-rose-400 transition hover:bg-rose-500 hover:text-white"
                            onClick={() => handleDelete(lead.id)}
                            type="button"
                          >
                            <Check size={14} aria-hidden="true" />
                          </button>
                          <button
                            aria-label={`Cancel delete for ${lead.company_name}`}
                            className="inline-flex items-center justify-center rounded-md border border-nexa-border bg-nexa-surface p-2 text-zinc-400 transition hover:border-zinc-500 hover:text-zinc-200"
                            onClick={() => setConfirmDeleteId(null)}
                            type="button"
                          >
                            <X size={14} aria-hidden="true" />
                          </button>
                        </>
                      ) : (
                        <button
                          aria-label={`Delete record for ${lead.company_name}`}
                          className="inline-flex items-center justify-center rounded-md border border-nexa-border bg-nexa-surface p-2 text-zinc-600 transition hover:border-rose-500/40 hover:bg-[var(--nexa-rose-dim)] hover:text-rose-400"
                          onClick={() => setConfirmDeleteId(lead.id)}
                          type="button"
                        >
                          <Trash2 size={14} aria-hidden="true" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
                {/* Expanded Detail Row */}
                {selectedLeadId === lead.id && (
                  <tr key={`${lead.id}-detail`}>
                    <td className="p-0" colSpan={6}>
                      <div className="animate-fade-in space-y-4 border-b border-nexa-border bg-nexa-bg p-5">
                        <ConfidenceMeter confidence={lead.confidence} />
                        <div className="nexa-card p-4 space-y-3">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Extracted Contacts & Domain</h4>
                          
                          {/* Added Domain Link inside expanded view for easy access */}
                          <div className="mb-3">
                            <a href={`https://${lead.domain}`} target="_blank" rel="noreferrer" className="text-xs text-[var(--nexa-accent)] hover:underline flex items-center gap-1 w-fit">
                                {lead.domain} <span className="text-[10px]">↗</span>
                            </a>
                          </div>

                          {lead.contacts && lead.contacts.length > 0 ? (
                            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                              {lead.contacts.map((contact, i) => (
                                <div key={i} className="flex flex-col gap-1 rounded-lg border border-white/5 bg-white/5 p-3 hover:border-white/10 transition-colors">
                                  <span className="text-sm font-medium text-zinc-200">{contact.name}</span>
                                  <span className="text-xs text-zinc-400">{contact.title}</span>
                                  <a href={`mailto:${contact.email}`} className="text-xs text-[var(--nexa-accent)] hover:underline mt-1">{contact.email}</a>
                                  <div className="flex items-center gap-2 mt-2">
                                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase ${
                                      contact.confidence === 'verified' 
                                        ? 'bg-[var(--nexa-emerald-dim)] text-emerald-400 border border-emerald-500/20' 
                                        : 'bg-[var(--nexa-amber-dim)] text-amber-400 border border-amber-500/20'
                                    }`}>
                                      {contact.confidence}
                                    </span>
                                    {contact.source && (
                                      <span className="text-[10px] text-zinc-500">{contact.source}</span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="rounded-lg border border-white/5 bg-white/5 p-4 text-center">
                                <span className="text-xs text-zinc-500">No public contacts found on {lead.domain} during this sweep.</span>
                            </div>
                          )}
                        </div>

                        {/* Firmographics Block */}
                        <div className="nexa-card relative overflow-hidden p-4">
                          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Firmographics</h4>
                          <div className="grid grid-cols-3 gap-4 text-sm opacity-30 blur-[2px]">
                            <div className="flex flex-col">
                              <span className="text-[10px] uppercase text-zinc-500">Industry</span>
                              <span className="font-medium text-zinc-300">{lead.industry || '—'}</span>
                            </div>
                            <div className="flex flex-col">
                              <span className="text-[10px] uppercase text-zinc-500">Employees</span>
                              <span className="font-medium text-zinc-300">{lead.employee_count ?? '—'}</span>
                            </div>
                            <div className="flex flex-col">
                              <span className="text-[10px] uppercase text-zinc-500">Funding</span>
                              <span className="font-medium text-zinc-300">{lead.funding_stage || '—'}</span>
                            </div>
                          </div>
                          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                            <span className="rounded-full bg-zinc-900/90 px-3 py-1.5 text-xs font-medium text-zinc-300 shadow-xl backdrop-blur-md border border-white/5">
                              Will be Updated soon, test
                            </span>
                          </div>
                        </div>

                        <p className="nexa-card p-4 text-sm leading-6 text-zinc-400">
                          {lead.ai_verdict}
                        </p>
                      </div>
                      <ScoreBreakdown signals={lead.signals} dns_audit={lead.dns_audit} />
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
                          await fetch('http://localhost:8000/api/pipeline/run', { method: 'POST' });
                          alert('Discovery Pipeline Triggered! Data will populate shortly.');
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
