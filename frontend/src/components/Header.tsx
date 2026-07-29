import { Shield, Search, Bell, Sun, Moon } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

interface HeaderProps {
  status: 'loading' | 'success' | 'error';
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  isDark: boolean;
  setIsDark: (dark: boolean) => void;
}

export default function Header({ status, searchTerm, setSearchTerm, isDark, setIsDark }: HeaderProps) {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="nexa-card nexa-card-no-hover relative z-10 flex items-center justify-between px-5 py-2.5 w-full rounded-2xl shadow-xs border border-nexa-border">
      {/* 1. LEFT SECTION: Company Logo, Name & Status Pill */}
      <div className="flex items-center gap-2.5">
        <div
          className={`flex h-8 w-8 items-center justify-center rounded-xl border shadow-2xs transition-all duration-300 ${
            status === 'success'
              ? 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-400 border-emerald-300 dark:border-emerald-500/30'
              : 'bg-amber-100 dark:bg-amber-500/15 text-amber-800 dark:text-amber-400 border-amber-300 dark:border-amber-500/30 animate-pulse'
          }`}
        >
          <Shield size={17} strokeWidth={2.5} aria-hidden="true" />
        </div>

        <div className="flex flex-col justify-center">
          <h1 className="text-sm font-black tracking-tight text-slate-900 dark:text-zinc-100 leading-none">
            Prospector AI
          </h1>
          <div className="mt-0.5 text-[10px] font-bold font-mono tracking-tight flex items-center gap-1.5">
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
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500" /> System Offline
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 2. CENTER SECTION: Global Search Bar */}
      <div className="flex-1 max-w-lg mx-5 hidden md:block">
        <div className="relative flex items-center w-full">
          <Search
            size={14}
            className="absolute left-3 text-slate-400 dark:text-zinc-400 pointer-events-none"
            aria-hidden="true"
          />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search companies, intent signals, or keywords..."
            className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-slate-100/80 dark:bg-white/5 py-1.5 pl-9 pr-9 text-xs font-medium text-slate-900 dark:text-zinc-100 outline-none transition-all placeholder:text-slate-400 dark:placeholder:text-zinc-400 focus:border-emerald-500/50 focus:bg-white dark:focus:bg-white/10 shadow-inner"
          />
          <kbd className="absolute right-2.5 hidden sm:inline-flex items-center gap-0.5 rounded-md border border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/10 px-1.5 py-0.5 text-[10px] font-mono font-bold text-slate-500 dark:text-zinc-400">
            /
          </kbd>
        </div>
      </div>

      {/* 3. RIGHT SECTION: Notifications & Quick Theme Toggle */}
      <div className="flex items-center gap-2">
        {/* Notification Bell */}
        <div ref={notificationRef} className="relative">
          <button
            type="button"
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="relative flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-zinc-300 hover:text-slate-950 dark:hover:text-white transition"
            title="Notifications"
          >
            <Bell size={15} />
            <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-[#111118]" />
          </button>

          {/* Notification Popover */}
          {notificationsOpen && (
            <div className="notification-popover absolute right-0 mt-2 w-72 rounded-2xl border border-slate-200 dark:border-nexa-border bg-white dark:bg-[#181824] p-4 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 text-left">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/10 pb-2 mb-2">
                <span className="text-xs font-bold text-slate-900 dark:text-zinc-100">Notifications</span>
                <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/50 px-2 py-0.5 rounded-full">3 New</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5">
                  <p className="font-bold text-slate-900 dark:text-zinc-100">Pipeline Sweep Complete</p>
                  <p className="text-[11px] text-slate-600 dark:text-zinc-400 mt-0.5">15 new target companies discovered today.</p>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5">
                  <p className="font-bold text-slate-900 dark:text-zinc-100">High Intent Signal</p>
                  <p className="text-[11px] text-slate-600 dark:text-zinc-400 mt-0.5">Leland posted new series B partner request.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Quick Theme Toggle */}
        <button
          type="button"
          onClick={() => setIsDark(!isDark)}
          className="flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-zinc-300 hover:text-slate-950 dark:hover:text-white transition"
          title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
        >
          {isDark ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
}
