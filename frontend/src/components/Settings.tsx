import { Shield, Key, Bell, Database, Target, Save, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { fetchIntents, updateIntents, type IntentConfig } from '../lib/api';

export default function Settings() {
  const [intents, setIntents] = useState<IntentConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIntents().then(data => {
      setIntents(data);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  const handleSaveIntents = async () => {
    if (!intents) return;
    setSaving(true);
    try {
      await updateIntents(intents);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };
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
          {/* Intent Keywords Section */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-2">
              <Target size={14} /> Intent Signals Configuration
            </h3>
            <div className="p-4 rounded-lg border border-white/5 bg-white/5 space-y-4">
              {loading ? (
                <div className="flex items-center gap-2 text-zinc-400 text-sm">
                  <Loader2 className="animate-spin" size={16} /> Loading intents...
                </div>
              ) : intents ? (
                <>
                  <div>
                    <label className="block text-xs font-medium text-zinc-400 mb-1">Extraction Keywords (comma separated)</label>
                    <textarea 
                      className="w-full bg-black/20 border border-white/10 rounded-md p-2 text-sm text-zinc-200 focus:outline-none focus:border-[var(--nexa-accent)]"
                      rows={2}
                      value={intents.extraction_keywords.join(', ')}
                      onChange={e => setIntents({...intents, extraction_keywords: e.target.value.split(',').map(s => s.trim()).filter(Boolean)})}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-400 mb-1">News Queries (one per line)</label>
                    <textarea 
                      className="w-full bg-black/20 border border-white/10 rounded-md p-2 text-sm text-zinc-200 focus:outline-none focus:border-[var(--nexa-accent)]"
                      rows={3}
                      value={intents.news_queries.join('\n')}
                      onChange={e => setIntents({...intents, news_queries: e.target.value.split('\n').map(s => s.trim()).filter(Boolean)})}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-400 mb-1">Job Role Search Term (JobSpy)</label>
                    <input 
                      type="text"
                      className="w-full bg-black/20 border border-white/10 rounded-md p-2 text-sm text-zinc-200 focus:outline-none focus:border-[var(--nexa-accent)]"
                      value={intents.jobspy_search_term || ''}
                      onChange={e => setIntents({...intents, jobspy_search_term: e.target.value})}
                    />
                  </div>
                  <div className="flex justify-end">
                    <button 
                      onClick={handleSaveIntents}
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-md bg-[var(--nexa-accent)] text-nexa-bg hover:brightness-110 transition disabled:opacity-50"
                    >
                      {saving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
                      Save Intents
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-zinc-500 text-sm">Failed to load intents.</div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
