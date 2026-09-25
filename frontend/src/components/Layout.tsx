import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Settings,
  Upload,
  BarChart3,
  Brain,
  GitBranch,
  DollarSign,
  Briefcase,
  FolderPlus,
  AlertTriangle,
  Loader2,
  X
} from 'lucide-react';
import clsx from 'clsx';
import { orgDataApi } from '../services/api';

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Upload CSV', href: '/upload', icon: Upload },
  { name: 'Metrics', href: '/metrics', icon: BarChart3 },
  { name: 'AI Analysis', href: '/analysis', icon: Brain },
  { name: 'Work Activities', href: '/work-activities', icon: Briefcase },
  { name: 'Org Chart', href: '/org-chart', icon: GitBranch },
  { name: 'Grade Config', href: '/grades', icon: DollarSign },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [clearing, setClearing] = useState(false);

  const handleNewProject = () => {
    setShowConfirmModal(true);
  };

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

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-4">
          <h1 className="text-xl font-bold">Org Design Analyzer</h1>
          <p className="text-sm text-gray-400 mt-1">Analyze & Optimize</p>
        </div>

        <nav className="mt-4 flex-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 text-sm transition-colors',
                  isActive
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* New Project Button */}
        <div className="p-4 border-t border-gray-700">
          <button
            onClick={handleNewProject}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <FolderPlus className="w-4 h-4" />
            New Project
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <main className="p-8">
          {children}
        </main>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-amber-100 rounded-full">
                  <AlertTriangle className="w-6 h-6 text-amber-600" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Start New Project?</h2>
                <button
                  onClick={() => setShowConfirmModal(false)}
                  className="ml-auto p-1 hover:bg-gray-100 rounded"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              <p className="text-gray-600 mb-4">
                This will clear all current data including:
              </p>
              <ul className="text-sm text-gray-600 mb-6 space-y-1 ml-4">
                <li>&#8226; Uploaded org structure data</li>
                <li>&#8226; Calculated metrics</li>
                <li>&#8226; AI analysis results</li>
                <li>&#8226; Work activities analysis</li>
              </ul>
              <p className="text-sm text-gray-500 mb-6">
                Your Claude API key and grade configuration will be preserved.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowConfirmModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  disabled={clearing}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmClear}
                  disabled={clearing}
                  className="flex-1 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors flex items-center justify-center gap-2"
                >
                  {clearing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Clearing...
                    </>
                  ) : (
                    <>
                      <FolderPlus className="w-4 h-4" />
                      Start Fresh
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
