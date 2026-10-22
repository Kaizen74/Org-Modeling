import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { orgDataApi } from '../services/api';
import type { UploadResponse } from '../types';
import { PageHeader, Section, StatTile, Callout } from '../components/ui';

const COLUMNS: Array<{ name: string; need: 'Required' | 'Recommended' | 'Optional'; what: string }> = [
  { name: 'Name', need: 'Required', what: 'Person’s name (shown on screen; never sent to the AI)' },
  { name: 'Job Title', need: 'Required', what: 'Role title' },
  { name: 'Grade', need: 'Required', what: 'e.g. SVP, H8, TL' },
  { name: 'Level', need: 'Required', what: '1 = top; checked against the reporting chain' },
  { name: 'Line Manager', need: 'Required', what: 'Manager’s name or Employee ID; “Top of Org” for the top' },
  { name: 'Employee ID', need: 'Recommended', what: 'Unique per person — keeps people with the same name apart' },
  { name: 'Department', need: 'Recommended', what: 'Enables the department view and department-scoped design' },
  { name: 'Salary', need: 'Recommended', what: 'Annual base; otherwise taken from the grade table' },
  { name: 'Line Manager ID', need: 'Optional', what: 'Removes guesswork when managers share a name' },
  { name: 'Work Type', need: 'Optional', what: '“Operational” or “Knowledge” — sets the span benchmark directly' },
  { name: 'Work Activities', need: 'Optional', what: 'What the role does — powers the work activities analysis' },
  { name: 'Job Description', need: 'Optional', what: 'Longer role description' },
];

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const accept = (f?: File) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.csv')) {
      setError('Please choose a CSV file (in Excel: File → Save As → CSV).');
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      setResult(await orgDataApi.uploadCsv(file));
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string | { errors?: string[] } } } }).response?.data?.detail;
      setError(typeof detail === 'object' && detail?.errors ? detail.errors.join('; ') : typeof detail === 'string' ? detail : 'The file could not be uploaded.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="01 · Diagnose — upload"
        title="Start from the organization as it is"
        lede="Upload one CSV of the organization: who each person is, their role and grade, and who they report to. Excel exports are fine, including its default encoding."
      />

      <div className="grid gap-8 lg:grid-cols-[1fr_1fr]">
        <div>
          <div
            onDrop={(e) => { e.preventDefault(); setDragging(false); accept(e.dataTransfer.files[0]); }}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
            role="button"
            tabIndex={0}
            className={clsx(
              'card cursor-pointer border-dashed py-14 text-center transition-colors',
              dragging ? 'border-primary-600 bg-primary-50' : 'hover:border-primary-600'
            )}
          >
            <input ref={fileInputRef} type="file" accept=".csv" onChange={(e) => accept(e.target.files?.[0])} className="hidden" />
            {file ? (
              <>
                <p className="eyebrow eyebrow-faint mb-2">Selected</p>
                <p className="font-display text-[22px] font-bold text-ink">{file.name}</p>
                <p className="mt-1 text-sm text-faint">{(file.size / 1024).toFixed(1)} KB · click to choose another</p>
              </>
            ) : (
              <>
                <p className="font-display text-[22px] font-bold text-ink">Drop the CSV here</p>
                <p className="mt-1 text-sm text-secondary">or click to browse</p>
              </>
            )}
          </div>

          {file && !result && (
            <button onClick={handleUpload} disabled={uploading} className="btn btn-primary mt-4 w-full justify-center">
              {uploading ? 'Reading the organization…' : 'Upload and analyze →'}
            </button>
          )}

          {error && <div className="mt-4"><Callout label="Upload failed" tone="attention">{error}</Callout></div>}

          {result?.success && (
            <div className="mt-6 fade-up">
              <p className="eyebrow mb-3">Uploaded</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <StatTile label="People" value={result.employee_count} />
                <StatTile label="Managers" value={result.manager_count} />
              </div>
              {result.validation_errors.length > 0 && (
                <div className="mt-4">
                  <Callout label={`${result.validation_errors.length} thing${result.validation_errors.length === 1 ? '' : 's'} to check in the data`} tone="developing">
                    <ul className="space-y-1">
                      {result.validation_errors.map((err, i) => <li key={i}><span className="mr-2 text-primary-600">·</span>{err}</li>)}
                    </ul>
                  </Callout>
                </div>
              )}
              <div className="mt-6 flex flex-wrap gap-3">
                <Link to="/" className="btn btn-primary">See the overview →</Link>
                <Link to="/metrics" className="btn btn-secondary">Structure</Link>
                <Link to="/work-activities" className="btn btn-quiet">Work activities</Link>
              </div>
            </div>
          )}
        </div>

        <Section eyebrow="What the file needs" className="mb-0">
          <ul className="card divide-y divide-hairline p-0">
            {COLUMNS.map((c) => (
              <li key={c.name} className="grid grid-cols-[150px_1fr] gap-3 px-5 py-2.5 text-sm">
                <span>
                  <span className="font-medium text-ink">{c.name}</span>
                  <span className={clsx('block text-[11px] font-semibold uppercase tracking-[.12em]', c.need === 'Required' ? 'text-primary-600' : 'text-faint')}>{c.need}</span>
                </span>
                <span className="text-secondary">{c.what}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-faint">
            No salaries? Set median salary per grade in <Link to="/grades" className="text-primary-600 underline">Grades &amp; salaries</Link> and costs are filled in.
          </p>
        </Section>
      </div>
    </>
  );
}
