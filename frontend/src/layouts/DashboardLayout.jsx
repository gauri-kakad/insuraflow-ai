import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FilePlus2,
  Cpu,
  FileSearch,
  UserCheck,
  History,
  BarChart3,
  ShieldCheck,
  LogOut,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { to: '/dashboard', label: 'Main Dashboard', icon: LayoutDashboard },
  { to: '/submit', label: 'Claim Submission', icon: FilePlus2 },
  { to: '/processing', label: 'AI Processing Center', icon: Cpu },
  { to: '/analysis', label: 'Claim Analysis', icon: FileSearch },
  { to: '/review', label: 'Human Review Center', icon: UserCheck },
  { to: '/history', label: 'Claim History', icon: History },
  { to: '/reports', label: 'Reports & Analytics', icon: BarChart3 },
];

export default function DashboardLayout() {
  const { user, logout, capabilities, preferDemoMode, setPreferDemoMode } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-navy-900 text-white flex flex-col shrink-0">
        <div className="h-16 px-5 flex items-center gap-3 border-b border-navy-800">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-base tracking-tight block leading-none">InsuraFlow AI</span>
            <span className="text-[11px] text-blue-200 mt-1 block">Motor Claims Intelligence</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-300 hover:bg-navy-800 hover:text-white'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-navy-800 text-xs text-slate-300 space-y-3">
          <div className="bg-navy-950/60 rounded-lg p-3 border border-navy-800">
            <p className="font-semibold text-white mb-1">Governance Guardrail</p>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Decision-support only. AI never approves or rejects claims automatically.
            </p>
          </div>
          <div className="flex items-center justify-between pt-1">
            <div className="truncate pr-2">
              <p className="font-medium text-white truncate">{user?.name}</p>
              <p className="text-[11px] text-slate-400 truncate">{user?.role}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-2 rounded-lg text-slate-300 hover:bg-navy-800 hover:text-white"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Motor Claims Adjudication Workspace
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Engine Mode Selector */}
            <div className="flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
              {capabilities.live_gemini_configured ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
              )}
              <span className="text-slate-600 font-medium">Execution Engine:</span>
              <select
                value={preferDemoMode ? 'demo' : 'live'}
                onChange={(e) => setPreferDemoMode(e.target.value === 'demo')}
                className="bg-transparent font-semibold text-navy-900 focus:outline-none cursor-pointer"
              >
                <option value="demo">Deterministic Demo Mode</option>
                <option value="live" disabled={!capabilities.live_gemini_configured}>
                  {capabilities.live_gemini_configured
                    ? `Live Gemini (${capabilities.gemini_model})`
                    : 'Live Gemini (API Key Missing)'}
                </option>
              </select>
            </div>
          </div>
        </header>

        {/* Page Body */}
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
