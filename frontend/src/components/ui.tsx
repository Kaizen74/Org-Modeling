/**
 * Shared building blocks in the OrgDesign Playbook style.
 * Status is never shown by colour alone: every status pairs colour with a glyph or word.
 */
import type { ReactNode } from 'react';
import clsx from 'clsx';

export function PageHeader({
  eyebrow,
  title,
  lede,
  actions,
}: {
  eyebrow?: string;
  title: string;
  lede?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-10 flex flex-wrap items-end justify-between gap-6">
      <div className="max-w-3xl">
        {eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}
        <h1 className="text-[40px] leading-[1.12] tracking-[-0.3px]">{title}</h1>
        {lede && <p className="mt-4 text-[17px] leading-relaxed text-secondary max-w-[640px]">{lede}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </header>
  );
}

export function Section({
  eyebrow,
  title,
  lede,
  children,
  className,
  aside,
}: {
  eyebrow?: string;
  title?: string;
  lede?: ReactNode;
  children: ReactNode;
  className?: string;
  aside?: ReactNode;
}) {
  return (
    <section className={clsx('mb-14', className)}>
      {(eyebrow || title) && (
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-3xl">
            {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
            {title && <h2 className="text-[26px] leading-tight">{title}</h2>}
            {lede && <p className="mt-2 text-secondary max-w-[640px]">{lede}</p>}
          </div>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

/** A KPI tile: label, large serif number, one line of context. */
export function StatTile({
  label,
  value,
  sub,
  status,
  emphasis = false,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  status?: Status;
  emphasis?: boolean;
}) {
  return (
    <div className="card">
      <p className="eyebrow eyebrow-faint mb-3">{label}</p>
      <p className={clsx('display-number text-ink', emphasis ? 'text-[56px]' : 'text-[36px]')}>{value}</p>
      {(sub || status) && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-secondary">
          {status && <StatusPill status={status} />}
          {sub}
        </div>
      )}
    </div>
  );
}

export type Status = 'healthy' | 'developing' | 'attention' | 'neutral';

const STATUS_STYLE: Record<Status, { color: string; glyph: string; label: string }> = {
  healthy: { color: 'var(--color-score-green)', glyph: '✓', label: 'Healthy' },
  developing: { color: 'var(--color-score-amber)', glyph: '~', label: 'Developing' },
  attention: { color: 'var(--color-score-red)', glyph: '!', label: 'Needs attention' },
  neutral: { color: 'var(--color-faint)', glyph: '·', label: 'No data' },
};

/** Healthy ≥ 70 · Developing 50–69 · Needs attention < 50 (Playbook thresholds). */
export function scoreStatus(score: number | null | undefined): Status {
  if (score === null || score === undefined || Number.isNaN(score)) return 'neutral';
  if (score >= 70) return 'healthy';
  if (score >= 50) return 'developing';
  return 'attention';
}

export function StatusPill({ status, label }: { status: Status; label?: string }) {
  const s = STATUS_STYLE[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold"
      style={{ borderColor: s.color, color: s.color }}
    >
      <span aria-hidden>{s.glyph}</span>
      {label ?? s.label}
    </span>
  );
}

/** Span position against its benchmark: arrow + word, so it reads in greyscale. */
export function BenchmarkPill({ status }: { status: 'below' | 'within' | 'above' }) {
  const map = {
    below: { glyph: '↓', label: 'Below', color: 'var(--color-score-amber)' },
    within: { glyph: '✓', label: 'Within', color: 'var(--color-score-green)' },
    above: { glyph: '↑', label: 'Above', color: 'var(--color-score-red)' },
  }[status];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold"
      style={{ borderColor: map.color, color: map.color }}
    >
      <span aria-hidden>{map.glyph}</span>
      {map.label}
    </span>
  );
}

/** Plain-div score bar (0-100) coloured by status. */
export function ScoreBar({ score, label, detail }: { score: number; label?: string; detail?: ReactNode }) {
  const status = scoreStatus(score);
  return (
    <div>
      {(label || detail) && (
        <div className="mb-1.5 flex items-baseline justify-between gap-4 text-sm">
          <span className="font-medium text-ink">{label}</span>
          <span className="tabular text-secondary">{score}/100</span>
        </div>
      )}
      <div className="h-1.5 w-full rounded-full bg-track" role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.max(0, Math.min(100, score))}%`, background: STATUS_STYLE[status].color }}
        />
      </div>
      {detail && <p className="mt-1.5 text-xs text-faint">{detail}</p>}
    </div>
  );
}

export function ScoreLegend() {
  return (
    <p className="flex flex-wrap gap-4 text-xs text-faint">
      <span><span style={{ color: 'var(--color-score-green)' }}>✓</span> Healthy ≥ 70</span>
      <span><span style={{ color: 'var(--color-score-amber)' }}>~</span> Developing 50–69</span>
      <span><span style={{ color: 'var(--color-score-red)' }}>!</span> Needs attention &lt; 50</span>
    </p>
  );
}

/** Pill chip for tags (departments, roles, dimensions). */
export function Chip({ children, active = false, onClick }: { children: ReactNode; active?: boolean; onClick?: () => void }) {
  const Tag = onClick ? 'button' : 'span';
  return (
    <Tag
      onClick={onClick}
      className={clsx(
        'inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        active ? 'border-primary-600 bg-primary-50 text-primary-700' : 'border-hairline bg-white text-secondary',
        onClick && !active && 'hover:border-ink hover:text-ink'
      )}
    >
      {children}
    </Tag>
  );
}

/** White card with a coloured uppercase label (instead of tinted alert boxes). */
export function Callout({
  label,
  tone = 'neutral',
  children,
}: {
  label: string;
  tone?: 'neutral' | 'attention' | 'developing' | 'healthy' | 'accent';
  children: ReactNode;
}) {
  const color = {
    neutral: 'var(--color-faint)',
    attention: 'var(--color-score-red)',
    developing: 'var(--color-score-amber)',
    healthy: 'var(--color-score-green)',
    accent: 'var(--color-primary)',
  }[tone];
  return (
    <div className="card py-4">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[.14em]" style={{ color }}>{label}</p>
      <div className="text-sm text-secondary">{children}</div>
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: ReactNode; action?: ReactNode }) {
  return (
    <div className="card py-14 text-center">
      <h2 className="text-[26px]">{title}</h2>
      <p className="mx-auto mt-3 max-w-md text-secondary">{body}</p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex h-64 items-center justify-center gap-3 text-secondary" role="status">
      <span className="h-1.5 w-24 overflow-hidden rounded-full bg-track">
        <span className="block h-full w-1/3 animate-pulse rounded-full bg-primary-600" />
      </span>
      {label}…
    </div>
  );
}

export const formatMoney = (value: number) =>
  value >= 1_000_000 ? `$${(value / 1_000_000).toFixed(2)}M` : value >= 1_000 ? `$${Math.round(value / 1_000)}k` : `$${Math.round(value)}`;
