import { Clipboard, Loader2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { fetchPitcherMode, type PitcherModeResponse } from '../lib/api';

interface PitcherModeProps {
  id: string;
  company_name: string;
  onClose: () => void;
}

export default function PitcherMode({ id, company_name, onClose }: PitcherModeProps) {
  const [loading, setLoading] = useState(true);
  const [pitchData, setPitchData] = useState<PitcherModeResponse | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    fetchPitcherMode(id)
      .then((payload) => {
        if (isMounted) {
          setPitchData(payload);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setPitchData({
            lead_id: id,
            subject_line: `Error: Unable to generate pitch`,
            email_body: `Failed to fetch target email copy from the backend AI engine.\n\nError details: ${err.message}`,
          });
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [id, company_name]);

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full animate-slide-in flex-col border-l border-nexa-border bg-[#0a0a0f]/70 backdrop-blur-2xl p-6 shadow-2xl sm:w-[460px]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-nexa-border pb-4">
        <div>
          <h2
            className="text-sm font-bold uppercase tracking-wide"
            style={{ color: 'var(--nexa-accent)' }}
          >
            Pitcher Mode
          </h2>
          <p className="mt-1 text-xs text-zinc-500">
            Custom sequence context for {company_name}
          </p>
        </div>
        <button
          aria-label="Close Pitcher Mode"
          className="rounded-md border border-nexa-border bg-nexa-card p-2 text-zinc-500 transition hover:border-[var(--nexa-accent)]/40 hover:text-zinc-200"
          onClick={onClose}
          type="button"
        >
          <X size={15} aria-hidden="true" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto py-6">
        {loading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center font-mono text-xs text-zinc-600">
            <Loader2
              className="animate-spin"
              size={22}
              aria-hidden="true"
              style={{ color: 'var(--nexa-accent)' }}
            />
            Lazy loading targeted model template...
          </div>
        ) : (
          <div className="space-y-4">
            <label className="block space-y-2">
              <span className="block text-[11px] font-bold uppercase tracking-wider text-zinc-600">
                Generated Subject Line
              </span>
              <input
                className="w-full rounded-lg border border-nexa-border bg-nexa-card p-3 text-xs text-zinc-300 outline-none"
                readOnly
                type="text"
                value={pitchData?.subject_line ?? ''}
              />
            </label>
            <label className="block space-y-2">
              <span className="block text-[11px] font-bold uppercase tracking-wider text-zinc-600">
                Contextual Body Blueprint
              </span>
              <textarea
                className="h-72 w-full resize-none rounded-lg border border-nexa-border bg-nexa-card p-3 font-mono text-xs leading-6 text-zinc-400 outline-none"
                readOnly
                value={pitchData?.email_body ?? ''}
              />
            </label>
          </div>
        )}
      </div>

      {/* Action Button */}
      {!loading && (
        <button
          className="flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-xs font-bold text-nexa-bg transition hover:brightness-110"
          style={{ background: 'var(--nexa-accent)' }}
          onClick={() =>
            navigator.clipboard?.writeText(
              `${pitchData?.subject_line}\n\n${pitchData?.email_body}`
            )
          }
          type="button"
        >
          <Clipboard size={14} aria-hidden="true" />
          Copy Outreach Template
        </button>
      )}
    </div>
  );
}
