import { Shield, Key, Bell, Database } from 'lucide-react';

export default function Settings() {
  return (
    <div className="flex-1 overflow-y-auto pr-2">
      <div className="nexa-card p-6">
        <h2 className="text-xl font-bold text-zinc-100 mb-6">Pipeline Settings</h2>
        
        <div className="space-y-6">
          {/* API Keys Section */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-2">
              <Key size={14} /> API Configuration
            </h3>
            <div className="grid gap-3">
              <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-white/5">
                <div>
                  <div className="font-medium text-zinc-200">Gemini LLM Key</div>
                  <div className="text-xs text-zinc-400">Used for intent scoring and extraction</div>
                </div>
                <button className="px-3 py-1.5 text-xs font-medium rounded-md bg-white/10 hover:bg-white/20 transition">Edit</button>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-white/5">
                <div>
                  <div className="font-medium text-zinc-200">Clearbit API Key</div>
                  <div className="text-xs text-zinc-400">Used for firmographics fallback</div>
                </div>
                <button className="px-3 py-1.5 text-xs font-medium rounded-md bg-white/10 hover:bg-white/20 transition">Edit</button>
              </div>
            </div>
          </section>

          {/* Engine Section */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-2">
              <Database size={14} /> Pipeline Engine
            </h3>
            <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-white/5">
              <div>
                <div className="font-medium text-zinc-200">Autonomous Discovery Interval</div>
                <div className="text-xs text-zinc-400">Currently set to sweep every 12 hours</div>
              </div>
              <select className="bg-transparent border border-white/10 rounded-md px-2 py-1 text-sm text-zinc-300">
                <option>6 Hours</option>
                <option selected>12 Hours</option>
                <option>24 Hours</option>
              </select>
            </div>
          </section>

          {/* Notifications Section */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-2">
              <Bell size={14} /> Alerts
            </h3>
            <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-white/5">
              <div>
                <div className="font-medium text-zinc-200">Strong ICP Fit Alerts</div>
                <div className="text-xs text-zinc-400">Notify when a new lead scores &gt; 85</div>
              </div>
              <div className="h-5 w-9 rounded-full bg-[var(--nexa-emerald)] relative cursor-pointer">
                <div className="absolute right-1 top-0.5 h-4 w-4 rounded-full bg-white shadow" />
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
