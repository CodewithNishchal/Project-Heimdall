import { LayoutDashboard, ShieldAlert, BarChart3, Settings, Info } from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Dashboard', icon: LayoutDashboard, active: true },
  { label: 'Threat Intelligence', icon: ShieldAlert, active: false },
  { label: 'Analytics', icon: BarChart3, active: false },
  { label: 'Settings', icon: Settings, active: false },
  { label: 'Information', icon: Info, active: false },
] as const;

interface SidebarProps {
  currentView: string;
  setCurrentView: (view: string) => void;
}

export default function Sidebar({ currentView, setCurrentView }: SidebarProps) {
  return (
    <aside className="nexa-card hidden w-52 flex-col gap-4 p-4 lg:flex">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.label}
            type="button"
            onClick={() => setCurrentView(item.label.toLowerCase())}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition ${
              currentView === item.label.toLowerCase()
                ? 'bg-zinc-800/20 text-[var(--nexa-accent)] border border-black/5 dark:bg-white/10 dark:text-white dark:border-transparent'
                : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-white/5 dark:hover:text-zinc-200'
            }`}
          >
            <Icon size={17} aria-hidden="true" />
            {item.label}
          </button>
        );
      })}
    </aside>
  );
}
