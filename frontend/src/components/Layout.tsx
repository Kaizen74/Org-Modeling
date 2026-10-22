import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { orgDataApi } from '../services/api';

interface LayoutProps {
  children: React.ReactNode;
}

// The navigation follows an org design engagement: diagnose → design → implement
const stages: Array<{ number: string; title: string; items: Array<{ name: string; href: string; hint: string }> }> = [
  {
    number: '01',
    title: 'Diagnose',
    items: [
      { name: 'Overview', href: '/', hint: 'Health at a glance' },
      { name: 'Upload data', href: '/upload', hint: 'Org structure CSV' },
      { name: 'Structure', href: '/metrics', hint: 'Spans, layers, cost' },
      { name: 'Org chart', href: '/org-chart', hint: 'Reporting lines' },
      { name: 'Work activities', href: '/work-activities', hint: 'What the work is' },
    ],
  },
  {
    number: '02',
    title: 'Design',
    items: [
      { name: 'Archetype options', href: '/analysis', hint: 'Strategy-fit structures' },
    ],
  },
];

const setup = [
  { name: 'Grades & salaries', href: '/grades' },
  { name: 'Settings', href: '/settings' },
];

/** 2×2 mark in the four framework quadrant colours (Playbook wordmark). */
function Mark() {
  const colors = ['#C41E3A', '#4A5568', '#9C6B72', '#2D3748'];
  return (
    <span className="grid grid-cols-2 gap-[2px]" aria-hidden>
      {colors.map((c) => (
        <span key={c} className="block h-2 w-2" style={{ background: c }} />
      ))}
    </span>
  );
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [clearing, setClearing] = useState(false);

  const handleConfirmClear = async () => {
    setClearing(true);
    try {
      await orgDataApi.clearAll();
      setShowConfirmModal(false);
      navigate('/upload');
      // Force a page reload to clear all cached state
      window.location.reload();
    } catch (err) {
      console.error('Failed to clear data:', err);
      alert('Failed to clear data. Please try again.');
    } finally {
      setClearing(false);
    }
  };

  const isActive = (href: string) => location.pathname === href;

  return (
    <div className="min-h-screen flex bg-paper">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-hairline bg-white flex flex-col">
        <Link to="/" className="flex items-center gap-3 px-6 pt-7 pb-8 text-ink hover:text-ink">
          <Mark />
          <span className="font-display text-[18px] font-bold leading-tight">Org Design Analyzer</span>
        </Link>

        <nav className="flex-1 px-3" aria-label="Main">
          {stages.map((stage) => (
            <div key={stage.number} className="mb-7">
              <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-[.16em] text-faint">
                <span className="text-primary-600">{stage.number}</span> · {stage.title}
              </p>
              {stage.items.map((item) => (
                <Link
                  key={item.href}
                  to={item.href}
                  aria-current={isActive(item.href) ? 'page' : undefined}
                  className={clsx(
                    'group block rounded px-3 py-2 transition-colors',
                    isActive(item.href) ? 'bg-primary-50' : 'hover:bg-wash'
                  )}
                >
                  <span className={clsx('block text-[14px] font-medium', isActive(item.href) ? 'text-primary-700' : 'text-ink')}>
                    {item.name}
                  </span>
                  <span className="block text-[12px] text-faint">{item.hint}</span>
                </Link>
              ))}
            </div>
          ))}

          <div className="mb-6 hairline-t pt-5">
            <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-[.16em] text-faint">Setup</p>
            {setup.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                aria-current={isActive(item.href) ? 'page' : undefined}
                className={clsx(
                  'block rounded px-3 py-1.5 text-[14px] transition-colors',
                  isActive(item.href) ? 'bg-primary-50 text-primary-700 font-medium' : 'text-secondary hover:bg-wash hover:text-ink'
                )}
              >
                {item.name}
              </Link>
            ))}
          </div>
        </nav>

        <div className="p-5 hairline-t">
          <button onClick={() => setShowConfirmModal(true)} className="btn btn-quiet w-full justify-center">
            Start a new project
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <main className="mx-auto max-w-[1140px] px-10 py-12 fade-up" key={location.pathname}>
          {children}
        </main>
      </div>

      {/* Confirmation dialog */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40" role="dialog" aria-modal="true" aria-labelledby="new-project-title">
          <div className="card mx-4 w-full max-w-md p-8">
            <p className="eyebrow mb-2">New project</p>
            <h2 id="new-project-title" className="text-[26px] mb-4">Start from a clean slate?</h2>
            <p className="text-secondary mb-3">This clears the current project:</p>
            <ul className="mb-4 space-y-1 text-sm text-secondary">
              <li><span className="text-primary-600 mr-2">·</span>Uploaded org structure</li>
              <li><span className="text-primary-600 mr-2">·</span>Calculated metrics</li>
              <li><span className="text-primary-600 mr-2">·</span>AI and work activities analyses</li>
            </ul>
            <p className="mb-7 text-sm text-faint">Your Claude API key and grade configuration are kept.</p>
            <div className="flex gap-3">
              <button onClick={() => setShowConfirmModal(false)} className="btn btn-quiet flex-1 justify-center" disabled={clearing}>
                Cancel
              </button>
              <button onClick={handleConfirmClear} disabled={clearing} className="btn btn-primary flex-1 justify-center">
                {clearing ? 'Clearing…' : 'Start fresh'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
