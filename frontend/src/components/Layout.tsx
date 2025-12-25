import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Settings,
  Upload,
  BarChart3,
  Brain,
  GitBranch,
  DollarSign
} from 'lucide-react';
import clsx from 'clsx';

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Upload CSV', href: '/upload', icon: Upload },
  { name: 'Metrics', href: '/metrics', icon: BarChart3 },
  { name: 'AI Analysis', href: '/analysis', icon: Brain },
  { name: 'Org Chart', href: '/org-chart', icon: GitBranch },
  { name: 'Grade Config', href: '/grades', icon: DollarSign },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white">
        <div className="p-4">
          <h1 className="text-xl font-bold">Org Design Analyzer</h1>
          <p className="text-sm text-gray-400 mt-1">Analyze & Optimize</p>
        </div>

        <nav className="mt-4">
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
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
