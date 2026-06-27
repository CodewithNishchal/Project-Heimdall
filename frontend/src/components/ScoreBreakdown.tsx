import { Check, CircleAlert, ExternalLink } from 'lucide-react';
import type { DNSAuditObjective, ExtractedSignal } from '../types/lead';

interface ScoreBreakdownProps {
  signals: ExtractedSignal[];
  dns_audit: DNSAuditObjective;
}

function dnsTone(value: string) {
  if (value === 'Valid') return { color: 'var(--nexa-emerald)', bg: 'var(--nexa-emerald-dim)' };
  if (value.includes('Weak')) return { color: 'var(--nexa-amber)', bg: 'var(--nexa-amber-dim)' };
  return { color: 'var(--nexa-rose)', bg: 'var(--nexa-rose-dim)' };
}

export default function ScoreBreakdown({ signals, dns_audit }: ScoreBreakdownProps) {
  return (
    <section className="animate-fade-in grid grid-cols-1 gap-4 border-t border-nexa-border bg-nexa-bg p-5 lg:grid-cols-3">
      {/* Left Half — Evidence Log */}
      <div className="space-y-3 lg:col-span-2">
        <h3 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-zinc-600">
          <span
            className="inline-block h-1.5 w-1.5 rounded-full"
            style={{ background: 'var(--nexa-accent)' }}
          />
          Extraction Evidence Log
        </h3>
        {signals.length === 0 ? (
          <p className="py-8 text-center font-mono text-xs text-zinc-700">
            No signal evidence captured for this target.
          </p>
        ) : (
          <div className="space-y-2.5">
            {signals.map((signal) => (
              <article
                key={`${signal.signal_type}-${signal.verbatim_quote}`}
                className="nexa-card p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span
                    className="rounded border px-2 py-0.5 font-mono text-[11px] uppercase"
                    style={{
                      borderColor: 'var(--nexa-accent)',
                      background: 'var(--nexa-accent-dim)',
                      color: 'var(--nexa-accent)',
                    }}
                  >
                    {signal.signal_type}
                  </span>
                  <span
                    className={`flex items-center gap-1 font-mono text-[11px] ${
                      signal.quote_validated ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {signal.quote_validated ? (
                      <Check size={12} aria-hidden="true" />
                    ) : (
                      <CircleAlert size={12} aria-hidden="true" />
                    )}
                    {signal.quote_validated ? 'Verified' : 'Needs Review'} ({signal.similarity_score}
                    %)
                  </span>
                </div>
                <blockquote className="mt-3 border-l-2 border-nexa-border py-1 pl-3 font-mono text-[11px] italic leading-5 text-zinc-400">
                  "{signal.verbatim_quote}"
                </blockquote>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-zinc-600">
                  <span className="flex items-center gap-3">
                    <span>
                      Recency:{' '}
                      <span className="uppercase text-zinc-400">{signal.recency_label}</span>
                    </span>
                    {signal.source_url && signal.source_url !== 'N/A' && signal.source_url !== 'None' && (
                      <a
                        href={signal.source_url.startsWith('http') ? signal.source_url : `https://${signal.source_url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[var(--nexa-accent)] transition-colors hover:text-[var(--nexa-accent-bright)]"
                        title="View source article"
                      >
                        <ExternalLink size={11} />
                        Source
                      </a>
                    )}
                  </span>
                  <span>
                    Impact:{' '}
                    <span className="font-bold text-zinc-300">+{signal.score_contribution} pts</span>
                  </span>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      {/* Right Half — DNS Audit Status */}
      <aside className="space-y-3">
        <h3 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-zinc-600">
          <span
            className="inline-block h-1.5 w-1.5 rounded-full"
            style={{ background: 'var(--nexa-rose)' }}
          />
          Infrastructure Risk Matrix
        </h3>
        <div className="nexa-card p-4">
          <div className="grid grid-cols-3 gap-2 text-center font-mono text-[11px]">
            {(['spf', 'dkim', 'dmarc'] as const).map((key) => {
              const tone = dnsTone(dns_audit[key]);
              return (
                <div
                  key={key}
                  className="rounded-lg border border-nexa-border p-3"
                  style={{ background: tone.bg }}
                >
                  <span className="mb-1.5 block uppercase text-zinc-600">{key}</span>
                  <span className="font-semibold" style={{ color: tone.color }}>
                    {dns_audit[key]}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-4 space-y-2">
            <span className="block text-[11px] font-bold uppercase tracking-wider text-zinc-600">
              Identified Selling Angles
            </span>
            {dns_audit.issues.length > 0 ? (
              dns_audit.issues.map((issue) => (
                <p
                  key={issue}
                  className="flex items-start gap-2 text-[11px] leading-5 text-zinc-500"
                >
                  <CircleAlert
                    className="mt-0.5 shrink-0 text-rose-500"
                    size={12}
                    aria-hidden="true"
                  />
                  {issue}
                </p>
              ))
            ) : (
              <p className="text-[11px] leading-5 text-zinc-700">
                No active DNS risk angle detected.
              </p>
            )}
          </div>
        </div>
      </aside>
    </section>
  );
}
