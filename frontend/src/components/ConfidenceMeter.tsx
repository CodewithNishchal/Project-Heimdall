import { CheckCircle2, CircleAlert } from 'lucide-react';
import type { ConfidenceEvaluation } from '../types/lead';

interface ConfidenceMeterProps {
  confidence: ConfidenceEvaluation;
}

export default function ConfidenceMeter({ confidence }: ConfidenceMeterProps) {
  const isHighTrust = confidence.color === 'emerald';
  const percentage = confidence.total > 0
    ? Math.round((confidence.verified / confidence.total) * 100)
    : 0;

  return (
    <section className="nexa-card flex items-center justify-between p-4">
      <div className="space-y-1.5">
        <span className="block text-[11px] font-bold uppercase tracking-wider text-zinc-600">
          Verification Engine
        </span>
        <div className="flex items-center gap-2">
          {isHighTrust ? (
            <CheckCircle2 className="text-emerald-400" size={15} aria-hidden="true" />
          ) : (
            <CircleAlert size={15} aria-hidden="true" style={{ color: 'var(--nexa-accent)' }} />
          )}
          <span className="text-sm font-semibold text-zinc-200">{confidence.label}</span>
        </div>
      </div>
      <div className="text-right">
        <div className="flex items-baseline gap-1">
          <span
            className="font-mono text-2xl font-bold"
            style={{
              color: isHighTrust ? 'var(--nexa-emerald)' : 'var(--nexa-accent)',
            }}
          >
            {percentage}%
          </span>
        </div>
        <span className="font-mono text-[11px] text-zinc-600">
          Composite score
        </span>
      </div>
    </section>
  );
}
