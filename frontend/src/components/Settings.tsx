import { Shield, Key, Bell, Database, Target, Save, Loader2, Cpu, Wand2, Sliders, Check, RefreshCw, ChevronDown, ChevronUp, History, Sparkles, Clock, Trash2 } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { fetchIntents, updateIntents, generateICPWithAI, type IntentConfig, type AIICPResponse } from '../lib/api';

const DEFAULT_TEMPLATES = [
  {
    title: 'Recruitment Agency',
    desc: 'DevOps, Cybersecurity, ML (50-2000 emp)',
    prompt: 'Recruitment agency in USA targeting DevOps, Cybersecurity, and ML roles with 50-2000 employee headcount',
  },
  {
    title: 'FinTech B2B SaaS',
    desc: 'Fractional CMO & Growth (20-500 emp)',
    prompt: 'B2B SaaS companies in FinTech with 20-500 employees looking for Fractional CMOs and Growth Marketing partners',
  },
  {
    title: 'E-Commerce & Retail',
    desc: 'Shopify, Meta Ads, Local SEO',
    prompt: 'E-Commerce brands using Shopify looking for Meta Ads management, Google Ads, and Local SEO optimization',
  },
];

export default function Settings() {
  const [intents, setIntents] = useState<IntentConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  // Local raw text states to allow typing commas, spaces, and newlines smoothly
  const [rawKeywords, setRawKeywords] = useState('');
  const [rawTriggers, setRawTriggers] = useState('');
  const [rawTopics, setRawTopics] = useState('');
  const [rawNews, setRawNews] = useState('');
  const [rawSerper, setRawSerper] = useState('');
  const [rawJobspy, setRawJobspy] = useState('');
  const [minEmployees, setMinEmployees] = useState(10);
  const [maxEmployees, setMaxEmployees] = useState(2000);

  // AI Assistant states
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);

  // Collapsible configuration panel state (Closed by default)
  const [configOpen, setConfigOpen] = useState(false);
  const configSectionRef = useRef<HTMLDivElement>(null);

  // ICP History state (Persisted in localStorage)
  const [historyICPs, setHistoryICPs] = useState<Array<{ title: string; prompt: string; date: string }>>([]);

  useEffect(() => {
    // Load local storage history
    try {
      const savedHistory = localStorage.getItem('heimdall_icp_history');
      if (savedHistory) {
        setHistoryICPs(JSON.parse(savedHistory));
      }
    } catch (e) {
      console.error('Failed to parse ICP history', e);
    }

    fetchIntents().then(data => {
      setIntents(data);
      setRawKeywords((data.extraction_keywords || []).join(', '));
      setRawTriggers((data.social_triggers || []).join(', '));
      setRawTopics((data.social_topics || []).join(', '));
      setRawNews((data.news_queries || []).join('\n'));
      setRawSerper((data.serper_queries || []).join('\n'));
      setRawJobspy(data.jobspy_search_term || '');
      setMinEmployees(data.min_employees || 10);
      setMaxEmployees(data.max_employees || 2000);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  const saveToHistory = (promptText: string) => {
    if (!promptText.trim()) return;
    const shortTitle = promptText.length > 35 ? promptText.slice(0, 35) + '...' : promptText;
    const newItem = {
      title: shortTitle,
      prompt: promptText,
      date: new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    };

    setHistoryICPs(prev => {
      const filtered = prev.filter(item => item.prompt.toLowerCase() !== promptText.toLowerCase());
      const updated = [newItem, ...filtered].slice(0, 6);
      try {
        localStorage.setItem('heimdall_icp_history', JSON.stringify(updated));
      } catch (e) {
        console.error(e);
      }
      return updated;
    });
  };

  const handleClearHistory = () => {
    setHistoryICPs([]);
    localStorage.removeItem('heimdall_icp_history');
  };

  const handleSaveIntents = async () => {
    setSaving(true);
    const payloadToSave: IntentConfig = {
      extraction_keywords: rawKeywords.split(',').map(s => s.trim()).filter(Boolean),
      social_triggers: rawTriggers.split(',').map(s => s.trim()).filter(Boolean),
      social_topics: rawTopics.split(',').map(s => s.trim()).filter(Boolean),
      news_queries: rawNews.split('\n').map(s => s.trim()).filter(Boolean),
      serper_queries: rawSerper.split('\n').map(s => s.trim()).filter(Boolean),
      jobspy_search_term: rawJobspy.trim(),
      news_signals_query_template: intents?.news_signals_query_template || '',
      min_employees: minEmployees,
      max_employees: maxEmployees,
    };
    try {
      await updateIntents(payloadToSave);
      setIntents(payloadToSave);
      if (aiPrompt.trim()) {
        saveToHistory(aiPrompt.trim());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateAIICP = async (customPrompt?: string) => {
    const promptToUse = customPrompt || aiPrompt;
    if (!promptToUse.trim()) return;

    setAiGenerating(true);
    setAiSummary(null);
    try {
      const res: AIICPResponse = await generateICPWithAI(promptToUse);

      // Auto-populate all form fields dynamically while leaving them 100% editable
      if (res.jobspy_search_term) setRawJobspy(res.jobspy_search_term);
      if (res.extraction_keywords?.length) setRawKeywords(res.extraction_keywords.join(', '));
      if (res.social_triggers?.length) setRawTriggers(res.social_triggers.join(', '));
      if (res.social_topics?.length) setRawTopics(res.social_topics.join(', '));
      if (res.news_queries?.length) setRawNews(res.news_queries.join('\n'));
      if (res.serper_queries?.length) setRawSerper(res.serper_queries.join('\n'));
      if (res.min_employees) setMinEmployees(res.min_employees);
      if (res.max_employees) setMaxEmployees(res.max_employees);

      setAiSummary(res.summary_explanation || 'Successfully auto-populated settings from your ICP brief.');

      // 1. Automatically expand the Intent Configuration Box
      setConfigOpen(true);

      // 2. Save into ICP History
      saveToHistory(promptToUse);

      // 3. Automatically scroll down smoothly for user to inspect and edit configuration
      setTimeout(() => {
        configSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 350);

    } catch (err) {
      console.error('Failed to generate AI ICP settings:', err);
      alert('Failed to generate ICP settings with AI. Please check server logs.');
    } finally {
      setAiGenerating(false);
    }
  };

  const parsedTriggers = rawTriggers.split(',').map(s => s.trim()).filter(Boolean);
  const parsedTopics = rawTopics.split(',').map(s => s.trim()).filter(Boolean);
  const previewQuery = `(${ (parsedTriggers.map(t => `"${t}"`).join(' OR ')) || '"looking for"' }) ${ (parsedTopics.map(t => `"${t}"`).join(' OR ')) || '"marketing agency"' }`;

  return (
    <div className="flex-1 overflow-y-auto pr-2 pb-12 font-sans">
      <div className="nexa-card p-8 space-y-8 max-w-5xl mx-auto">
        
        {/* Settings Page Header */}
        <div className="flex items-center justify-between border-b border-nexa-border pb-5">
          <div className="space-y-1">
            <h2 className="text-2xl font-bold text-zinc-100 tracking-tight">Pipeline Settings</h2>
            <p className="text-xs text-zinc-400 font-medium">
              Configure autonomous search queries, ICP headcount thresholds, and AI co-pilot preferences.
            </p>
          </div>
        </div>

        {/* 1. AI ICP ASSISTANT CARD (UNCONGESTED, SPACIOUS CHAT BOX) */}
        <section className="side-drawer-card p-6 border border-[var(--nexa-accent)]/30 bg-[var(--nexa-accent-dim)] rounded-2xl space-y-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[var(--nexa-accent)] text-zinc-950 shadow-xs">
              <Cpu size={20} className="stroke-[2.5]" />
            </div>
            <div>
              <h3 className="text-base font-bold text-zinc-100 tracking-tight">
                AI ICP Assistant
              </h3>
              <p className="text-xs text-zinc-300 font-medium">
                Describe your Ideal Customer Profile in natural language. The AI will parse headcount, job terms, and intent queries automatically.
              </p>
            </div>
          </div>

          {/* Chat Input Box & Action */}
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <textarea
              className="flex-1 glass-input rounded-xl p-3.5 text-xs text-zinc-100 placeholder-zinc-500 border border-white/10 bg-nexa-surface focus:border-[var(--nexa-accent)] transition-all resize-none font-medium leading-relaxed"
              rows={3}
              placeholder="e.g. Target recruitment agencies in USA hiring for DevOps, Cybersecurity, ML roles, company headcount 50-2000, 6-8 years experience..."
              value={aiPrompt}
              onChange={e => setAiPrompt(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleGenerateAIICP();
                }
              }}
            />
            <button
              onClick={() => handleGenerateAIICP()}
              disabled={aiGenerating || !aiPrompt.trim()}
              className="px-6 py-4 rounded-xl font-bold text-xs bg-[var(--nexa-accent)] text-zinc-950 hover:brightness-110 transition-all flex items-center justify-center gap-2.5 whitespace-nowrap disabled:opacity-50 shadow-md self-end sm:self-stretch"
            >
              {aiGenerating ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
              Generate & Populate
            </button>
          </div>

          {/* AI Response Summary */}
          {aiSummary && (
            <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs font-medium flex items-center gap-2.5 animate-fade-in">
              <Check size={16} className="text-emerald-400 shrink-0" />
              <span>{aiSummary} Intent Configuration has expanded below for your review & editing.</span>
            </div>
          )}
        </section>

        {/* 2. ICP TEMPLATES & SAVED HISTORY BOX */}
        <section className="side-drawer-card p-6 rounded-2xl border border-nexa-border bg-nexa-surface space-y-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
              <History size={14} className="text-[var(--nexa-accent)]" /> ICP Templates & Prompt History
            </h3>
            {historyICPs.length > 0 && (
              <button
                onClick={handleClearHistory}
                className="text-[11px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition font-medium"
                title="Clear Prompt History"
              >
                <Trash2 size={12} /> Clear History
              </button>
            )}
          </div>

          {/* Pre-configured Templates Row */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold text-zinc-400 block uppercase tracking-wider">Quick Enterprise Templates:</span>
            <div className="flex flex-wrap gap-2.5">
              {DEFAULT_TEMPLATES.map((tmpl, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setAiPrompt(tmpl.prompt);
                    handleGenerateAIICP(tmpl.prompt);
                  }}
                  className="side-drawer-pill px-4 py-2 rounded-xl border border-[var(--nexa-accent)]/30 bg-[var(--nexa-accent-dim)] text-[var(--nexa-accent)] hover:bg-[var(--nexa-accent-glow)] transition-all text-xs font-semibold flex items-center gap-2 shadow-2xs"
                >
                  <Sparkles size={12} />
                  <span>{tmpl.title}</span>
                  <span className="text-[10px] opacity-75 font-normal">({tmpl.desc})</span>
                </button>
              ))}
            </div>
          </div>

          {/* User's Recent Prompt History Row */}
          {historyICPs.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-nexa-border">
              <span className="text-[11px] font-bold text-zinc-400 block uppercase tracking-wider flex items-center gap-1">
                <Clock size={12} /> Your Saved Recent ICP Prompts:
              </span>
              <div className="flex flex-wrap gap-2">
                {historyICPs.map((hist, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setAiPrompt(hist.prompt);
                      handleGenerateAIICP(hist.prompt);
                    }}
                    className="side-drawer-pill px-3.5 py-1.5 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-200 hover:border-[var(--nexa-accent)]/60 transition-all text-xs font-medium flex items-center gap-2 shadow-2xs"
                  >
                    <span>{hist.title}</span>
                    <span className="text-[10px] text-zinc-500 font-mono">{hist.date}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* 3. API CONFIGURATION */}
        <section className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <Key size={14} /> API Configuration
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="side-drawer-card flex items-center justify-between p-4 rounded-xl border border-nexa-border bg-nexa-surface">
              <div>
                <div className="font-bold text-zinc-100 text-xs">Gemini LLM Key</div>
                <div className="text-[11px] text-zinc-400 font-medium">Used for intent scoring and extraction</div>
              </div>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">Configured</span>
            </div>
            <div className="side-drawer-card flex items-center justify-between p-4 rounded-xl border border-nexa-border bg-nexa-surface">
              <div>
                <div className="font-bold text-zinc-100 text-xs">Clearbit & Serper API Keys</div>
                <div className="text-[11px] text-zinc-400 font-medium">Used for firmographics fallback and news discovery</div>
              </div>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">Configured</span>
            </div>
          </div>
        </section>

        {/* 4. TARGET COMPANY HEADCOUNT (ICP FILTER) */}
        <section className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <Sliders size={14} /> Target Company Headcount (ICP Filter)
          </h3>
          <div className="side-drawer-card grid grid-cols-1 sm:grid-cols-2 gap-4 p-5 rounded-2xl border border-nexa-border bg-nexa-surface">
            <div>
              <label className="block text-xs font-bold text-zinc-200 mb-1.5">Minimum Employee Headcount</label>
              <input
                type="number"
                className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface font-medium"
                value={minEmployees}
                onChange={e => setMinEmployees(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-zinc-200 mb-1.5">Maximum Employee Headcount</label>
              <input
                type="number"
                className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface font-medium"
                value={maxEmployees}
                onChange={e => setMaxEmployees(Number(e.target.value))}
              />
            </div>
          </div>
        </section>

        {/* 5. COLLAPSIBLE INTENT SIGNALS CONFIGURATION BOX (SCROLL TARGET) */}
        <section ref={configSectionRef} className="space-y-4 pt-2">
          {/* Expandable Accordion Header */}
          <div
            onClick={() => setConfigOpen(!configOpen)}
            className="side-drawer-card p-5 rounded-2xl border border-nexa-border bg-nexa-surface flex items-center justify-between cursor-pointer hover:border-[var(--nexa-accent)]/40 transition-all shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-indigo-950/80 text-indigo-300 border border-indigo-500/30">
                <Target size={16} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-zinc-100 tracking-tight flex items-center gap-2">
                  Intent Signals & Search Queries Configuration
                  <span className="px-2 py-0.5 rounded-full text-[10px] bg-nexa-surface border border-nexa-border text-zinc-400 font-mono font-normal">
                    {configOpen ? 'Open / Editable' : 'Collapsed (Click to Expand)'}
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 font-medium">
                  Review and manually edit job roles, extraction keywords, social triggers, and search queries.
                </p>
              </div>
            </div>

            <button className="p-2 rounded-xl border border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100 transition">
              {configOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>

          {/* Collapsible Form Body */}
          {configOpen && (
            <div className="side-drawer-card p-6 rounded-2xl border border-nexa-border bg-nexa-surface space-y-5 animate-fade-in shadow-sm">
              {loading ? (
                <div className="flex items-center gap-2 text-zinc-400 text-xs py-4">
                  <Loader2 className="animate-spin" size={14} /> Loading intent configuration...
                </div>
              ) : intents ? (
                <>
                  <div>
                    <label className="block text-xs font-bold text-zinc-200 mb-1.5">
                      Job Role Search Term (JobSpy) — <span className="text-[var(--nexa-accent)] font-semibold">Fully Editable</span>
                    </label>
                    <input
                      type="text"
                      className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface focus:border-[var(--nexa-accent)] transition-all font-medium"
                      value={rawJobspy}
                      onChange={e => setRawJobspy(e.target.value)}
                      placeholder="e.g. Chief Marketing Officer, VP of Marketing, Head of Growth"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-zinc-200 mb-1.5">
                      Extraction Keywords (comma separated) — <span className="text-[var(--nexa-accent)] font-semibold">Fully Editable</span>
                    </label>
                    <textarea
                      className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface focus:border-[var(--nexa-accent)] transition-all font-medium"
                      rows={2}
                      value={rawKeywords}
                      onChange={e => setRawKeywords(e.target.value)}
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-zinc-200 mb-1.5">
                        Social Triggers (comma separated) — <span className="text-[var(--nexa-accent)] font-semibold">Fully Editable</span>
                      </label>
                      <textarea
                        className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface focus:border-[var(--nexa-accent)] transition-all font-medium"
                        rows={2}
                        value={rawTriggers}
                        onChange={e => setRawTriggers(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-zinc-200 mb-1.5">
                        Social Topics (comma separated) — <span className="text-[var(--nexa-accent)] font-semibold">Fully Editable</span>
                      </label>
                      <textarea
                        className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface focus:border-[var(--nexa-accent)] transition-all font-medium"
                        rows={2}
                        value={rawTopics}
                        onChange={e => setRawTopics(e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Boolean Preview Box */}
                  <div className="nexa-card rounded-xl p-3.5 text-xs font-mono border border-nexa-border bg-nexa-bg">
                    <span className="font-sans block mb-1 font-bold text-zinc-300">Generated Boolean Query Preview (Reddit & X):</span>
                    <span className="text-[var(--nexa-accent)]">{previewQuery}</span>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-zinc-200 mb-1.5">
                      News Queries (one per line) — <span className="text-[var(--nexa-accent)] font-semibold">Fully Editable</span>
                    </label>
                    <textarea
                      className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface focus:border-[var(--nexa-accent)] transition-all font-medium"
                      rows={3}
                      value={rawNews}
                      onChange={e => setRawNews(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-zinc-200 mb-1.5">
                      Serper Google Search Queries (one per line) — <span className="text-[var(--nexa-accent)] font-semibold">Fully Editable</span>
                    </label>
                    <textarea
                      className="w-full glass-input rounded-xl p-3 text-xs text-zinc-100 border border-nexa-border bg-nexa-surface focus:border-[var(--nexa-accent)] transition-all font-medium"
                      rows={2}
                      value={rawSerper}
                      onChange={e => setRawSerper(e.target.value)}
                    />
                  </div>

                  <div className="flex justify-end pt-3">
                    <button
                      onClick={handleSaveIntents}
                      disabled={saving}
                      className="flex items-center gap-2 px-6 py-3 text-xs font-bold rounded-xl bg-[var(--nexa-accent)] text-zinc-950 hover:brightness-110 transition-all disabled:opacity-50 shadow-md"
                    >
                      {saving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
                      Save Intent Configuration
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-zinc-500 text-xs py-4">Failed to load intents configuration.</div>
              )}
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
