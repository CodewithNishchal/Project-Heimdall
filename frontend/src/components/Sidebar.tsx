import { LayoutGrid, Workflow, MessageSquare, Target, Settings as SettingsIcon, Shield } from 'lucide-react';

interface SidebarProps {
  currentView: string;
  setCurrentView: (view: string) => void;
  isDark?: boolean;
  setIsDark?: (dark: boolean) => void;
  status: 'loading' | 'success' | 'error';
}

export default function Sidebar({ currentView, setCurrentView, status }: SidebarProps) {
  const navItems = [
    { label: 'Dashboard', key: 'dashboard', icon: LayoutGrid },
    { label: 'Run Pipeline', key: 'pipeline', icon: Workflow },
    { label: 'Chats', key: 'social media posts', icon: MessageSquare },
    { label: 'Track Records', key: 'statistics', icon: Target },
  ];

  return (
    <div className="group relative w-[62px] shrink-0 hidden lg:block z-30">
      {/* Background Dim Overlay when hovering over sidebar */}
      <div className="fixed inset-0 bg-slate-950/20 dark:bg-black/40 backdrop-blur-[1px] pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-30" />

      {/* Floating Overlay Sidebar */}
      <aside className="sidebar-container flex flex-col justify-between h-[calc(100vh-2rem)] w-[62px] group-hover:w-[255px] absolute top-0 left-0 transition-all duration-300 ease-in-out px-2 group-hover:px-3.5 py-3.5 rounded-3xl font-sans z-30 overflow-hidden shadow-md group-hover:shadow-2xl border border-slate-200 dark:border-nexa-border">
        
        {/* 1. BRANDING: Prospector AI Name, Status & Light Green Shield Icon */}
        <div className="space-y-4 pt-1">
          <div className="flex items-center justify-center group-hover:justify-start px-0 group-hover:px-1 py-1 overflow-hidden transition-all duration-300">
            <div
              className={`relative flex h-9 w-9 group-hover:h-10 group-hover:w-10 items-center justify-center rounded-2xl border shadow-xs shrink-0 transition-all duration-300 ${
                status === 'success'
                  ? 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-400 border-emerald-300 dark:border-emerald-500/30'
                  : 'bg-amber-100 dark:bg-amber-500/15 text-amber-800 dark:text-amber-400 border-amber-300 dark:border-amber-500/30 animate-pulse'
              }`}
            >
              <Shield size={22} strokeWidth={2.5} aria-hidden="true" />
            </div>
            <div className="opacity-0 w-0 group-hover:w-auto group-hover:opacity-100 transition-all duration-300 whitespace-nowrap overflow-hidden group-hover:pl-3 flex flex-col justify-center">
              <h1 className="text-base font-black tracking-tight text-slate-900 dark:text-zinc-100 leading-none">
                Prospector AI
              </h1>
              <div className="mt-1 text-[11px] font-bold font-mono tracking-tight flex items-center gap-1.5">
                {status === 'loading' && (
                  <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> Connecting…
                  </span>
                )}
                {status === 'success' && (
                  <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.8)] animate-pulse" /> Engine Active
                  </span>
                )}
                {status === 'error' && (
                  <span className="text-rose-600 dark:text-rose-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500" /> Disconnected
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="border-b border-transparent group-hover:border-slate-200 dark:group-hover:border-nexa-border transition-colors duration-300" />
        </div>

        {/* 2. CONTENT ALIGNMENT: Navigation Items */}
        <div className="flex-1 flex flex-col justify-start space-y-2.5 py-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.key;
            return (
              <button
                key={item.label}
                type="button"
                onClick={() => setCurrentView(item.key)}
                className={`flex items-center justify-center group-hover:justify-start rounded-2xl p-2.5 group-hover:p-3 w-full text-left text-sm transition-all duration-200 overflow-hidden ${
                  isActive
                    ? 'bg-gradient-to-r from-emerald-100 via-emerald-50 to-teal-100/90 dark:from-emerald-950/70 dark:via-emerald-900/50 dark:to-teal-950/60 text-emerald-950 dark:text-emerald-300 border border-emerald-400/80 dark:border-emerald-500/40 shadow-[0_2px_12px_rgba(16,185,129,0.18)] font-black scale-[1.02]'
                    : 'text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-950 dark:hover:text-zinc-100 font-extrabold border border-transparent'
                }`}
              >
                <div className="shrink-0 flex items-center justify-center">
                  <Icon
                    size={22}
                    className={`transition-colors ${
                      isActive
                        ? 'text-emerald-900 dark:text-emerald-300 stroke-[2.5]'
                        : 'text-slate-600 dark:text-zinc-400 stroke-[2]'
                    }`}
                  />
                </div>
                <span className="opacity-0 w-0 group-hover:w-auto group-hover:opacity-100 transition-all duration-300 whitespace-nowrap group-hover:pl-3">
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* 3. SETTINGS ANCHORED AT THE BOTTOM */}
        <div className="pt-3 border-t border-transparent group-hover:border-slate-200 dark:group-hover:border-nexa-border transition-colors duration-300">
          <button
            type="button"
            onClick={() => setCurrentView('settings')}
            className={`flex items-center justify-center group-hover:justify-start rounded-2xl p-2.5 group-hover:p-3 w-full text-left text-sm transition-all duration-200 overflow-hidden ${
              currentView === 'settings'
                ? 'bg-gradient-to-r from-emerald-100 via-emerald-50 to-teal-100/90 dark:from-emerald-950/70 dark:via-emerald-900/50 dark:to-teal-950/60 text-emerald-950 dark:text-emerald-300 border border-emerald-400/80 dark:border-emerald-500/40 shadow-[0_2px_12px_rgba(16,185,129,0.18)] font-black scale-[1.02]'
                : 'text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-950 dark:hover:text-zinc-100 font-extrabold border border-transparent'
            }`}
          >
            <div className="shrink-0 flex items-center justify-center">
              <SettingsIcon
                size={22}
                className={`transition-colors ${
                  currentView === 'settings'
                    ? 'text-emerald-900 dark:text-emerald-300 stroke-[2.5]'
                    : 'text-slate-600 dark:text-zinc-400 stroke-[2]'
                }`}
              />
            </div>
            <span className="opacity-0 w-0 group-hover:w-auto group-hover:opacity-100 transition-all duration-300 whitespace-nowrap group-hover:pl-3 font-extrabold">
              Settings
            </span>
          </button>
        </div>

      </aside>
    </div>
  );
}