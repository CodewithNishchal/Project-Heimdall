import React, { useEffect, useState, useMemo } from 'react';
import { Trash2, Search, RefreshCw, ExternalLink, MessageSquare } from 'lucide-react';
import { fetchSocialPosts, deleteSocialPost, triggerSocialSweep } from '../lib/api';
import type { SocialPost } from '../types/lead';

const TABS = ['All', 'Google', 'Reddit', 'X', 'Facebook', 'LinkedIn', 'Threads'];

// Platform Brand Icon Components matching the screenshot
const GoogleLogo = () => (
  <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
  </svg>
);

const RedditLogo = () => (
  <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="#FF4500">
    <circle cx="12" cy="12" r="10" />
    <path fill="#FFF" d="M16.67 13.14c.04.18.06.36.06.55 0 2.8-3.01 5.07-6.73 5.07s-6.73-2.27-6.73-5.07c0-.19.02-.37.06-.55A2.04 2.04 0 0 1 2 11.23c0-1.12.91-2.03 2.03-2.03.5 0 .96.18 1.32.48 1.4-.99 3.28-1.63 5.37-1.7l1.14-5.36 3.73.79c.08-.47.49-.83.98-.83 1.01 0 1.83.82 1.83 1.83s-.82 1.83-1.83 1.83c-.93 0-1.7-.7-1.81-1.61l-3.23-.69-.9 4.25c2.14.05 4.07.69 5.5 1.7.36-.31.82-.49 1.33-.49 1.12 0 2.03.91 2.03 2.03 0 .76-.42 1.42-1.04 1.77zM9.07 12.3c-.63 0-1.14.51-1.14 1.14s.51 1.14 1.14 1.14 1.14-.51 1.14-1.14-.51-1.14-1.14-1.14zm5.86 0c-.63 0-1.14.51-1.14 1.14s.51 1.14 1.14 1.14 1.14-.51 1.14-1.14-.51-1.14-1.14-1.14z"/>
  </svg>
);

const XLogo = () => (
  <svg className="w-3 h-3 shrink-0 fill-current" viewBox="0 0 24 24">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </svg>
);

const FacebookLogo = () => (
  <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="10" fill="#1877F2"/>
    <path fill="#FFF" d="M15 12h-2v7h-3v-7H8.5V9.5H10V8c0-2 1-3 3-3h2v2.5h-1c-.8 0-1 .2-1 1v1h2l-.5 2.5z"/>
  </svg>
);

const LinkedInLogo = () => (
  <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24">
    <rect width="20" height="20" x="2" y="2" fill="#0A66C2" rx="4"/>
    <path fill="#FFF" d="M6.5 8.5h2.5V17H6.5V8.5zM7.75 5C6.92 5 6.25 5.67 6.25 6.5S6.92 8 7.75 8 9.25 7.33 9.25 6.5 8.58 5 7.75 5zM11 8.5h2.4v1.2h.03c.33-.63 1.14-1.3 2.37-1.3 2.54 0 3 1.67 3 3.85V17h-2.5v-3.85c0-.92-.02-2.1-1.28-2.1-1.28 0-1.48 1-1.48 2.03V17H11V8.5z"/>
  </svg>
);

const ThreadsLogo = () => (
  <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="10" fill="#000000"/>
    <path fill="#FFF" d="M14.88 11.53c-.1-.04-.26-.06-.5-.06-.41 0-.82.12-1.1.33-.3.23-.46.56-.46.94 0 .39.15.7.45.92.29.22.7.33 1.15.33.51 0 .95-.14 1.28-.43.34-.3.51-.72.51-1.24v-.25c0-.52-.16-.94-.48-1.24-.32-.3-.77-.45-1.35-.45h-.22c-.66 0-1.18.17-1.55.51-.37.34-.56.81-.56 1.4 0 .58.19 1.05.57 1.39.38.34.9.51 1.57.51.6 0 1.1-.14 1.5-.42.4-.28.6-.68.6-1.2h1.4c0 .87-.33 1.55-.99 2.04-.66.49-1.5.73-2.51.73-1.09 0-1.95-.3-2.58-.9-.63-.6-.94-1.43-.94-2.49 0-1.07.31-1.9.94-2.5.63-.6 1.49-.9 2.58-.9h.3c1.07 0 1.9.29 2.5.87.6.58.9 1.36.9 2.34v.53c0 .86-.28 1.53-.84 2.01-.56.48-1.3.72-2.22.72-.8 0-1.47-.19-2-.57-.53-.38-.8-.92-.8-1.62 0-.68.27-1.21.81-1.58.54-.37 1.25-.56 2.13-.56h.31v-.05z"/>
  </svg>
);

function getTabIcon(tab: string) {
  switch (tab.toLowerCase()) {
    case 'google': return <GoogleLogo />;
    case 'reddit': return <RedditLogo />;
    case 'x': return <XLogo />;
    case 'facebook': return <FacebookLogo />;
    case 'linkedin': return <LinkedInLogo />;
    case 'threads': return <ThreadsLogo />;
    default: return null;
  }
}

function timeAgo(dateString: string | number) {
  if (!dateString) return 'Just now';
  let t = 0;
  if (typeof dateString === 'number') {
    t = dateString;
  } else if (!isNaN(Number(dateString))) {
    t = Number(dateString);
  } else {
    t = new Date(dateString).getTime();
  }
  if (isNaN(t) || t <= 0) return 'Just now';
  if (t < 10000000000) t = t * 1000;

  const seconds = Math.floor((Date.now() - t) / 1000);
  if (isNaN(seconds) || seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w ago`;
}

function isPostOlderThan30Days(post: SocialPost): boolean {
  let t = 0;
  const dateStr = post.published_at || (post as any).created_at;
  if (!dateStr) return false;
  if (!isNaN(Number(dateStr))) {
    t = Number(dateStr);
  } else {
    t = new Date(dateStr).getTime();
  }
  if (isNaN(t) || t <= 0) return false;
  if (t < 10000000000) t = t * 1000;
  
  const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
  return (Date.now() - t) > thirtyDaysMs;
}

function formatLastFetched(date: Date | null): string {
  if (!date) return 'Just now';
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 15) return 'Just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function SocialPostsView() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [activeTab, setActiveTab] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [lastFetchedTime, setLastFetchedTime] = useState<Date | null>(() => {
    const saved = localStorage.getItem('social_posts_last_fetched');
    if (saved) {
      const parsed = new Date(saved);
      if (!isNaN(parsed.getTime())) {
        if (Date.now() - parsed.getTime() < 24 * 60 * 60 * 1000) {
          return parsed;
        }
      }
    }
    return new Date();
  });
  const [timeAgoText, setTimeAgoText] = useState<string>('Just now');

  useEffect(() => {
    const updateText = () => {
      setTimeAgoText(formatLastFetched(lastFetchedTime));
    };
    updateText();
    const interval = setInterval(updateText, 5000);
    return () => clearInterval(interval);
  }, [lastFetchedTime]);

  const loadPosts = async () => {
    setLoading(true);
    try {
      const data = await fetchSocialPosts(activeTab === 'All' ? undefined : activeTab.toLowerCase());
      setPosts(data);

      const saved = localStorage.getItem('social_posts_last_fetched');
      if (saved) {
        const parsed = new Date(saved);
        if (!isNaN(parsed.getTime()) && Date.now() - parsed.getTime() < 24 * 60 * 60 * 1000) {
          setLastFetchedTime(parsed);
          return;
        }
      }

      if (data.length > 0) {
        const nowMs = Date.now();
        const timestamps = data
          .map((p: any) => {
            if (p.created_at) {
              const cat = new Date(p.created_at).getTime();
              if (!isNaN(cat) && cat > 0 && nowMs - cat < 24 * 60 * 60 * 1000) return cat;
            }
            return 0;
          })
          .filter((t) => t > 0);

        if (timestamps.length > 0) {
          const newest = new Date(Math.max(...timestamps));
          setLastFetchedTime(newest);
          localStorage.setItem('social_posts_last_fetched', newest.toISOString());
        } else {
          const defaultTime = new Date();
          setLastFetchedTime(defaultTime);
          localStorage.setItem('social_posts_last_fetched', defaultTime.toISOString());
        }
      } else {
        const defaultTime = new Date();
        setLastFetchedTime(defaultTime);
        localStorage.setItem('social_posts_last_fetched', defaultTime.toISOString());
      }
    } catch (err) {
      console.error('Failed to fetch posts', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPosts();
  }, [activeTab]);

  const handleFetch = async () => {
    setFetching(true);
    const clickTime = new Date();
    setLastFetchedTime(clickTime);
    localStorage.setItem('social_posts_last_fetched', clickTime.toISOString());
    try {
      const res = await triggerSocialSweep();
      const fetchTime = res.last_fetched_at ? new Date(res.last_fetched_at) : new Date();
      setLastFetchedTime(fetchTime);
      localStorage.setItem('social_posts_last_fetched', fetchTime.toISOString());
      await loadPosts();
    } catch (err) {
      console.error('Failed to trigger sweep', err);
    } finally {
      setFetching(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setPosts((prev) => prev.filter((p) => p.id !== id));
    try {
      await deleteSocialPost(id);
    } catch (err) {
      console.error('Failed to delete post', err);
      loadPosts();
    }
  };

  const filteredPosts = useMemo(() => {
    let list = posts.filter((p) => !isPostOlderThan30Days(p));
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (p) =>
          p.content.toLowerCase().includes(q) ||
          p.company_name?.toLowerCase().includes(q) ||
          p.author_name?.toLowerCase().includes(q) ||
          p.author_handle?.toLowerCase().includes(q) ||
          p.keyword_matched?.toLowerCase().includes(q)
      );
    }
    return [...list].sort((a, b) => {
      const timeA = a.published_at ? new Date(a.published_at).getTime() : 0;
      const timeB = b.published_at ? new Date(b.published_at).getTime() : 0;
      return timeB - timeA;
    });
  }, [posts, searchQuery]);

  const getPlatformBadge = (platform: string) => {
    const plat = platform.toLowerCase();
    let label = platform.charAt(0).toUpperCase() + platform.slice(1);
    let icon = getTabIcon(platform);

    if (plat === 'google' || plat === 'google q&a') {
      label = 'Google';
    } else if (plat === 'reddit') {
      label = 'Reddit';
    } else if (plat === 'linkedin') {
      label = 'LinkedIn';
    } else if (plat === 'facebook') {
      label = 'Facebook';
    } else if (plat === 'x' || plat === 'twitter') {
      label = 'X';
    } else if (plat === 'threads') {
      label = 'Threads';
    }

    return (
      <span className="bg-[#EFF6FF] dark:bg-sky-950/50 text-[#0284C7] dark:text-sky-300 text-[11px] font-bold px-2.5 py-1 rounded-full inline-flex items-center gap-1.5 border border-sky-100 dark:border-sky-900/40">
        {icon}
        <span>{label}</span>
      </span>
    );
  };

  const isPostHot = (post: SocialPost) => {
    const postDate = new Date(post.published_at);
    const now = new Date();
    if (!isNaN(postDate.getTime())) {
      const diffDays = Math.floor((now.getTime() - postDate.getTime()) / (1000 * 60 * 60 * 24));
      return diffDays < 10;
    }
    return true;
  };

  const getIntentBadge = (post: SocialPost) => {
    const isHot = isPostHot(post);
    if (isHot) {
      return (
        <span className="bg-[#ECFDF5] dark:bg-emerald-950/50 text-[#059669] dark:text-emerald-300 text-[11px] font-bold px-2.5 py-1 rounded-full inline-flex items-center gap-1 border border-emerald-100 dark:border-emerald-900/40">
          <span>Hot</span>
        </span>
      );
    }
    return (
      <span className="bg-[#FEF3C7] dark:bg-amber-950/50 text-[#D97706] dark:text-amber-300 text-[11px] font-bold px-2.5 py-1 rounded-full inline-flex items-center gap-1 border border-amber-100 dark:border-amber-900/40">
        <span>Warm</span>
      </span>
    );
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 w-full bg-transparent space-y-3.5 font-sans overflow-hidden">
      
      {/* 1. Header Bar (Fixed / Pin to top) */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 shrink-0 pt-0.5">
        
        {/* Left Title Section with Amber Speech Bubble Icon */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#FDE9BD] dark:bg-amber-900/40 flex items-center justify-center shrink-0 shadow-2xs border border-[#FCD34D]/40">
            <MessageSquare size={19} className="text-[#9A5B00] dark:text-amber-300 stroke-[2.3]" />
          </div>
          <div>
            <h1 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-zinc-100 tracking-tight">
              Social Media Signals
            </h1>
            <p className="text-xs text-slate-500 dark:text-zinc-400 font-normal mt-0.5">
              Discover active intent posts from Scrape Creators
            </p>
          </div>
        </div>

        {/* Right Search Input + Action Button */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full lg:w-auto">
          {/* Search Input */}
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-500 pointer-events-none" size={14} />
            <input
              type="text"
              placeholder="Search keywords or posts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-full border border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-900/90 py-1.5 pl-9 pr-4 text-xs font-medium text-slate-800 dark:text-zinc-100 outline-none transition-all placeholder:text-slate-400 dark:placeholder:text-zinc-500 focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 shadow-2xs"
            />
          </div>

          {/* Fetch Intent Posts Button */}
          <button
            onClick={handleFetch}
            disabled={fetching}
            className="social-fetch-btn flex items-center justify-center gap-2 px-4 py-2 text-xs rounded-full transition-all disabled:opacity-50 whitespace-nowrap shrink-0 cursor-pointer"
          >
            <RefreshCw className={`stroke-[2.5] ${fetching ? 'animate-spin' : ''}`} size={14} />
            <span>Fetch Intent Posts</span>
          </button>
        </div>
      </div>

      {/* 2. Stats Bar (Fixed / Pin to top) */}
      <div className="flex flex-wrap items-center gap-2.5 shrink-0">
        {/* Threads Found */}
        <div className="bg-white dark:bg-zinc-900 px-3.5 py-1.5 rounded-2xl border border-slate-200/80 dark:border-zinc-800 shadow-2xs flex items-center gap-2.5 text-xs">
          <span className="text-slate-500 dark:text-zinc-400 font-medium">Threads Found</span>
          <span className="font-extrabold text-xs text-[#2563EB] dark:text-blue-400">{filteredPosts.length}</span>
        </div>

        {/* Hot Leads */}
        <div className="bg-white dark:bg-zinc-900 px-3.5 py-1.5 rounded-2xl border border-slate-200/80 dark:border-zinc-800 shadow-2xs flex items-center gap-2.5 text-xs">
          <span className="text-slate-500 dark:text-zinc-400 font-medium">Hot Leads</span>
          <span className="font-extrabold text-xs text-[#16A34A] dark:text-emerald-400">{filteredPosts.filter(isPostHot).length}</span>
        </div>

        {/* Warm Leads */}
        <div className="bg-white dark:bg-zinc-900 px-3.5 py-1.5 rounded-2xl border border-slate-200/80 dark:border-zinc-800 shadow-2xs flex items-center gap-2.5 text-xs">
          <span className="text-slate-500 dark:text-zinc-400 font-medium">Warm Leads</span>
          <span className="font-extrabold text-xs text-[#D97706] dark:text-amber-400">{Math.max(0, filteredPosts.length - filteredPosts.filter(isPostHot).length)}</span>
        </div>

        {/* Last Fetched */}
        <div className="bg-white dark:bg-zinc-900 px-3.5 py-1.5 rounded-2xl border border-slate-200/80 dark:border-zinc-800 shadow-2xs flex items-center gap-2.5 text-xs">
          <span className="text-slate-500 dark:text-zinc-400 font-medium">Last Fetched</span>
          <span className="font-semibold text-xs text-slate-700 dark:text-zinc-300">{timeAgoText}</span>
        </div>
      </div>

      {/* 3. Platform Filter Tabs (Fixed / Pin to top) */}
      <div className="flex items-center gap-2 overflow-x-auto pb-0.5 shrink-0 scrollbar-none">
        {TABS.map((tab) => {
          const isActive = activeTab === tab;
          const icon = getTabIcon(tab);
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-semibold transition-all whitespace-nowrap cursor-pointer shadow-2xs ${
                isActive
                  ? 'bg-[#10B981] text-white font-extrabold shadow-sm'
                  : 'bg-white dark:bg-zinc-900 border border-slate-200/80 dark:border-zinc-800 text-slate-700 dark:text-zinc-300 hover:bg-slate-50 dark:hover:bg-zinc-800'
              }`}
            >
              {icon}
              <span>{tab}</span>
            </button>
          );
        })}
      </div>

      {/* 4. Content Feed Grid (Individually Scrollable Section) */}
      <div className="flex-1 min-h-0 overflow-y-auto pr-1 pb-6 pt-1">
        {loading ? (
          <div className="flex justify-center items-center h-48">
            <RefreshCw className="animate-spin text-emerald-500" size={28} />
          </div>
        ) : filteredPosts.length === 0 ? (
          <div className="bg-white dark:bg-zinc-900 rounded-2xl p-8 text-center border border-slate-200/80 dark:border-zinc-800 space-y-2.5 max-w-md mx-auto my-8 shadow-xs">
            <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-zinc-800 flex items-center justify-center mx-auto text-slate-400">
              <Search size={20} />
            </div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-zinc-200">No intent posts found</h3>
            <p className="text-xs text-slate-500 dark:text-zinc-400">
              Try adjusting your filter or search query, or click "Fetch Intent Posts" to run a fresh sweep.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {filteredPosts.map((post) => {
              const rawContent = (post.content || '').replace(/["“”]/g, '').trim();
              const cleanContent = rawContent
                .replace(/^[^—–\n]+(?:\(@[^\)]+\)|•|\bInstagram\b|\bLinkedIn\b|\bTwitter\b|\bReddit\b|\bFacebook\b)[^—–\n]*[—–]\s*/gi, '')
                .replace(/^[^—–\n]*\(@[^\)]+\)[^—–\n]*[—–]\s*/gi, '')
                .trim();
              
              const displayContent = cleanContent || rawContent;
              const rawTitle = (post.summary || displayContent.split('\n')[0] || displayContent || '').replace(/^["“”']+|["“”']+$/g, '').trim();
              const titleText = `"${rawTitle}"`;
              const snippetText = post.summary ? displayContent : (displayContent.split('\n').slice(1).join(' ') || displayContent);

              return (
                <div
                  key={post.id}
                  className="bg-white dark:bg-zinc-900 rounded-2xl p-4 border border-slate-200/80 dark:border-zinc-800 shadow-xs flex flex-col justify-between transition-all duration-200 hover:shadow-md group"
                >
                  <div>
                    {/* Card Header Row: Platform Badge + Intent Badge (Left), Timestamp (Right) */}
                    <div className="flex items-center justify-between gap-2 mb-2.5">
                      <div className="flex items-center gap-1.5">
                        {getPlatformBadge(post.platform)}
                        {getIntentBadge(post)}
                      </div>
                      <span className="text-[11px] font-normal text-slate-400 dark:text-zinc-500 shrink-0">
                        {timeAgo(post.published_at)}
                      </span>
                    </div>

                    {/* Card Title (Single Set of Quotes) */}
                    <h3 className="text-xs sm:text-sm font-extrabold text-slate-900 dark:text-zinc-100 leading-snug tracking-tight line-clamp-2 mb-1.5">
                      {titleText}
                    </h3>

                    {/* Card Snippet */}
                    <p className="text-[11px] sm:text-xs font-normal text-slate-500 dark:text-zinc-400 leading-relaxed line-clamp-2 mb-3">
                      {snippetText}
                    </p>
                  </div>

                  {/* Card Actions (Bottom Right) */}
                  <div className="flex items-center justify-end gap-1.5 pt-1">
                    {/* Delete Icon Button */}
                    <button
                      type="button"
                      onClick={(e) => handleDelete(post.id, e)}
                      className="p-1.5 rounded-lg border border-slate-200 dark:border-zinc-800 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-slate-50 dark:hover:bg-zinc-800 transition cursor-pointer"
                      title="Delete Post"
                    >
                      <Trash2 size={13} />
                    </button>

                    {/* View Post Button */}
                    <a
                      href={post.post_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1 bg-white dark:bg-zinc-900 text-emerald-700 dark:text-emerald-400 font-semibold text-[11px] rounded-lg border border-emerald-200/80 dark:border-emerald-900/60 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 transition-all cursor-pointer shadow-2xs"
                    >
                      <span>View post</span>
                      <ExternalLink size={11} className="stroke-[2.2]" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
