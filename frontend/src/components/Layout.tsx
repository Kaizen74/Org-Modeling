import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import {
  LayoutDashboard,
  FolderKanban,
  GitCompare,
  Settings,
  Menu,
  X,
  Building2,
} from 'lucide-react'

const navItems = [
  { path: '/projects', label: 'Projects', icon: FolderKanban },
  { path: '/compare', label: 'Compare', icon: GitCompare },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebar } = useAppStore()

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside
        className={`bg-slate-900 text-white transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        <div className="p-4 flex items-center justify-between border-b border-slate-700">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <Building2 className="h-6 w-6 text-blue-400" />
              <span className="font-semibold text-lg">OrgDesign Pro</span>
            </div>
          )}
          <button
            onClick={toggleSidebar}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            {sidebarCollapsed ? <Menu className="h-5 w-5" /> : <X className="h-5 w-5" />}
          </button>
        </div>

        <nav className="p-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname.startsWith(item.path)

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
