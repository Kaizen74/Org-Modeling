/** Settings: span range for each manager type, and the words that mark a supervisory role. App-wide. */
import { useEffect, useState } from 'react';
import { structureApi } from '../services/api';
import type { ManagerTypeKey, StructureSettings as Settings } from '../types';
import { Callout, Section } from './ui';

const detailOf = (e: unknown, fallback: string) =>
  (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? fallback;

export default function StructureSettings() {
  const [data, setData] = useState<Settings | null>(null);
  const [ranges, setRanges] = useState<Record<string, [string, string]>>({});
  const [words, setWords] = useState('');
  const [notice, setNotice] = useState<{ tone: 'healthy' | 'attention'; text: string } | null>(null);

  const load = (s: Settings) => {
    setData(s);
    setRanges(Object.fromEntries(Object.entries(s.type_ranges).map(([k, [lo, hi]]) => [k, [String(lo), String(hi)]])));
    setWords(s.supervisory_words.join(', '));
  };
  useEffect(() => { structureApi.settings().then(load).catch(() => undefined); }, []);
  if (!data) return null;

  const save = async () => {
    setNotice(null);
    try {
      load(await structureApi.saveSettings({
        type_ranges: Object.fromEntries(Object.entries(ranges).map(([k, [lo, hi]]) => [k, [Number(lo), Number(hi)]])) as Record<ManagerTypeKey, [number, number]>,
        supervisory_words: words.split(',').map((w) => w.trim()).filter(Boolean),
      }));
      setNotice({ tone: 'healthy', text: 'Saved. Spans are recalculated with these ranges and words.' });
    } catch (e) {
      setNotice({ tone: 'attention', text: detailOf(e, 'Could not save.') });
    }
  };

  return (
    <>
      <Section eyebrow="Structure" title="Span ranges by manager type" lede={data.note}>
        <div className="card p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                <th className="px-5 py-3">Manager type</th>
                <th className="px-3 py-3">From</th>
                <th className="px-3 py-3">To</th>
              </tr>
            </thead>
            <tbody>
              {data.manager_types.map((t) => (
                <tr key={t.key} className="hairline-b last:border-0">
                  <td className="px-5 py-2.5">
                    <p className="font-medium text-ink">{t.label}</p>
                    <p className="text-xs text-faint">{t.description} · starting point {t.starting_range[0]}–{t.starting_range[1]}</p>
                  </td>
                  {[0, 1].map((i) => (
                    <td key={i} className="px-3 py-2.5">
                      <input type="number" min={1} max={200} className="input w-20 py-1" aria-label={`${t.label} ${i ? 'to' : 'from'}`}
                        value={ranges[t.key]?.[i] ?? ''}
                        onChange={(e) => setRanges((r) => ({ ...r, [t.key]: (i ? [r[t.key][0], e.target.value] : [e.target.value, r[t.key][1]]) as [string, string] }))} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-faint">A manager with no type keeps the Work Type rule: 10–20 for Operational, 5–10 otherwise.</p>
      </Section>

      <Section eyebrow="Structure" title="Words that mark a supervisory role"
        lede="Someone whose job title contains one of these (or whose manager type you've confirmed) but who has nobody reporting to them is a sign of broken reporting lines. Separate words with commas.">
        <input className="input" aria-label="Supervisory words" value={words} onChange={(e) => setWords(e.target.value)} />
        <p className="mt-1.5 text-xs text-faint">Starts with frontline words only ({data.default_supervisory_words.join(', ')}): titles with Manager, Head or Lead are often specialists. Add them if they supervise in your organization.</p>
      </Section>

      {notice && <div className="mb-4"><Callout label={notice.tone === 'healthy' ? 'Saved' : 'Not saved'} tone={notice.tone}>{notice.text}</Callout></div>}
      <div className="mb-14 flex gap-3">
        <button className="btn btn-primary" onClick={save}>Save structure settings</button>
        <button className="btn btn-quiet" onClick={async () => { load(await structureApi.resetSettings()); setNotice({ tone: 'healthy', text: 'Back to the starting ranges and words.' }); }}>Reset to starting points</button>
      </div>
    </>
  );
}
