import React, { useEffect, useState, useMemo } from 'react';
import { Trash2, Search, RefreshCw, MessageSquare, ExternalLink } from 'lucide-react';
import { fetchSocialPosts, deleteSocialPost, triggerSocialSweep } from '../lib/api';
import type { SocialPost } from '../types/lead';
const TABS = ['All', 'Google', 'Reddit', 'X', 'Facebook', 'LinkedIn', 'Threads'];

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
  if (!date) return 'Recently';
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (isNaN(seconds) || seconds < 10) return 'Just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(seconds / 60);
  if (hours < 24) return `${hours}h ago`;
  return 'Recently';
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
        // If saved timestamp is within 24 hours, use it; otherwise clear stale date
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

      // If no recent fetch timestamp exists, fallback to newest post created_at or default to now
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
    // Reset timer immediately on button click
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
    // Automatically purge/filter out posts older than 30 days
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
    // Sort so most recent posts appear first (newest published_at timestamp first)
    return [...list].sort((a, b) => {
      const timeA = a.published_at ? new Date(a.published_at).getTime() : 0;
      const timeB = b.published_at ? new Date(b.published_at).getTime() : 0;
      return timeB - timeA;
    });
  }, [posts, searchQuery]);

  const getPlatformBadge = (platform: string) => {
    const plat = platform.toLowerCase();
    let label = platform.charAt(0).toUpperCase() + platform.slice(1);
    let bgClass = 'bg-zinc-900 text-white';

    if (plat === 'google' || plat === 'google q&a') {
      label = 'Google';
      bgClass = 'bg-[#4285F4] text-white';
    } else if (plat === 'reddit') {
      label = 'Reddit';
      bgClass = 'bg-[#FF4500] text-white';
    } else if (plat === 'linkedin') {
      label = 'LinkedIn';
      bgClass = 'bg-[#0A66C2] text-white';
    } else if (plat === 'facebook') {
      label = 'Facebook';
      bgClass = 'bg-[#1877F2] text-white';
    } else if (plat === 'instagram') {
      label = 'Instagram';
      bgClass = 'bg-gradient-to-r from-purple-600 via-pink-600 to-amber-500 text-white';
    } else if (plat === 'x' || plat === 'twitter') {
      label = 'X';
      bgClass = 'bg-black text-white border border-white/20';
    } else if (plat === 'threads') {
      label = 'Threads';
      bgClass = 'bg-zinc-900 text-white border border-white/10';
    }

    return (
      <span className={`${bgClass} text-[11px] font-bold px-2.5 py-0.5 rounded-full inline-flex items-center gap-1 shadow-xs`}>
        <MessageSquare size={11} className="stroke-[2.5]" />
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
        <span className="bg-emerald-600 text-white text-[11px] font-bold px-2.5 py-0.5 rounded-full inline-flex items-center gap-1 shadow-xs">
          <span>🔥</span> Hot
        </span>
      );
    }
    return (
      <span className="bg-amber-600 text-white text-[11px] font-bold px-2.5 py-0.5 rounded-full inline-flex items-center gap-1 shadow-xs">
        Warm
      </span>
    );
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 sm:h-[calc(100vh-6rem)] space-y-3.5 sm:overflow-hidden">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0">
        <div className="flex items-center">
          <div
            style={{
              background: 'radial-gradient(circle at 30% 30%, #F5C563 0%, #E5A93C 55%, #B37E25 100%)',
              borderRadius: '50%',
              width: '38px',
              height: '38px',
              minWidth: '38px',
              minHeight: '38px',
              maxWidth: '38px',
              maxHeight: '38px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              marginRight: '1rem',
            }}
            className="shadow-md shadow-[#E5A93C]/25"
          >
            <MessageSquare size={17} style={{ color: '#121215' }} className="stroke-[2.3]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-100 tracking-tight">Social Media Signals</h1>
            <p className="text-xs text-slate-500 dark:text-zinc-400 font-medium">Discover active intent posts from Scrape Creators</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full sm:w-auto">
          {/* 1. Fetch Intent Posts Button (Appears First on Mobile, Full Width) */}
          <button
            onClick={handleFetch}
            disabled={fetching}
            style={{ backgroundColor: 'var(--nexa-accent)', color: '#000000' }}
            className="flex items-center justify-center gap-2 px-3.5 py-2.5 sm:py-2 text-xs font-bold rounded-xl hover:opacity-90 transition-all shadow-md disabled:opacity-50 whitespace-nowrap shrink-0 w-full sm:w-auto order-1 sm:order-2"
          >
            {fetching ? <RefreshCw className="animate-spin" size={14} /> : <RefreshCw size={14} />}
            Fetch Intent Posts
          </button>

          {/* 2. Search Bar Input (Appears Below Fetch Intent Posts on Mobile, Full Width) */}
          <div className="relative w-full sm:w-64 order-2 sm:order-1">
            <Search
              style={{ left: '0.875rem' }}
              className="absolute top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-400 pointer-events-none hidden sm:block"
              size={14}
            />
            <input
              type="text"
              placeholder="Search keywords or posts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-white/5 py-2 px-3 sm:pl-9 sm:pr-4 text-xs font-medium text-slate-900 dark:text-zinc-100 outline-none transition-all placeholder:text-slate-400 dark:placeholder:text-zinc-400 text-center placeholder:text-center sm:text-left sm:placeholder:text-left focus:border-amber-500/50 focus:bg-white dark:focus:bg-white/10 shadow-inner backdrop-blur-md"
            />
          </div>
        </div>
      </div>

      {/* Summary KPI 4-Box Bar (2x2 Grid on Mobile, Flex Row on Desktop) */}
      <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-2.5 text-xs shrink-0 w-full">
        {/* Box 1: Threads Found */}
        <div className="bg-white dark:bg-white/5 text-slate-700 dark:text-zinc-300 p-2.5 sm:px-3.5 sm:py-1.5 rounded-2xl sm:rounded-full font-medium border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between sm:justify-start gap-1.5">
          <span className="text-[11px] sm:text-xs text-slate-500 dark:text-zinc-400 font-semibold">Threads Found:</span>
          <strong className="font-extrabold text-sm sm:text-xs text-slate-900 dark:text-zinc-100">{filteredPosts.length}</strong>
        </div>

        {/* Box 2: Hot Leads */}
        <div className="bg-white dark:bg-white/5 text-slate-700 dark:text-zinc-300 p-2.5 sm:px-3.5 sm:py-1.5 rounded-2xl sm:rounded-full font-medium border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between sm:justify-start gap-1.5">
          <span className="text-[11px] sm:text-xs text-slate-500 dark:text-zinc-400 font-semibold">Hot Leads:</span>
          <strong className="font-extrabold text-sm sm:text-xs text-emerald-600 dark:text-emerald-400">{filteredPosts.filter(isPostHot).length}</strong>
        </div>

        {/* Box 3: Warm */}
        <div className="bg-white dark:bg-white/5 text-slate-700 dark:text-zinc-300 p-2.5 sm:px-3.5 sm:py-1.5 rounded-2xl sm:rounded-full font-medium border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between sm:justify-start gap-1.5">
          <span className="text-[11px] sm:text-xs text-slate-500 dark:text-zinc-400 font-semibold">Warm Leads:</span>
          <strong className="font-extrabold text-sm sm:text-xs text-amber-600 dark:text-amber-400">{Math.max(0, filteredPosts.length - filteredPosts.filter(isPostHot).length)}</strong>
        </div>

        {/* Box 4: Last Fetched */}
        <div className="bg-white dark:bg-white/5 text-slate-700 dark:text-zinc-300 p-2.5 sm:px-3.5 sm:py-1.5 rounded-2xl sm:rounded-full font-medium border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between sm:justify-start gap-1.5">
          <span className="text-[11px] sm:text-xs text-slate-500 dark:text-zinc-400 font-semibold">Last Fetched:</span>
          <strong className="font-extrabold text-xs text-slate-900 dark:text-zinc-100 truncate">{timeAgoText}</strong>
        </div>
      </div>

      {/* Platform Filter Tabs (Grid Structure on Mobile, Compact Flex Row on Desktop) */}
      <div className="grid grid-cols-4 gap-1.5 sm:flex sm:items-center sm:gap-2 pb-1 shrink-0 w-full sm:w-auto">
        {TABS.map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`w-full sm:w-auto text-center justify-center px-2 py-1.5 sm:px-4 sm:py-1 rounded-full text-[11px] sm:text-xs font-semibold border transition-all whitespace-nowrap shadow-xs shrink-0 ${
                isActive
                  ? 'bg-amber-500 text-black border-amber-500 font-extrabold shadow-xs'
                  : 'border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-slate-950 dark:hover:text-white'
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* Content Feed — Fitted strictly to vertical height on desktop */}
      <div className="flex-1 min-h-0 sm:overflow-y-auto pr-1 pb-16 sm:pb-4">
        {loading ? (
          <div className="flex justify-center items-center h-48">
            <RefreshCw className="animate-spin text-[var(--nexa-accent)]" size={28} />
          </div>
        ) : filteredPosts.length === 0 ? (
          <div className="nexa-card flex flex-col justify-center items-center h-60 p-6">
            <MessageSquare size={36} className="text-zinc-500 mb-3" />
            <p className="text-zinc-300 text-sm font-medium">No intent posts discovered for this category.</p>
            <p className="text-zinc-500 text-xs mt-1">Try clicking "Fetch Intent Posts" to run a fresh sweep.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredPosts.map((post) => {
              const tags = (post.keyword_matched || 'web design')
                .split(',')
                .flatMap(k => k.trim().split(' '))
                .filter(Boolean)
                .slice(0, 4);

              // Clean content by stripping names, handles, quotes, and platform header prefixes
              const rawContent = (post.content || '').replace(/["“”]/g, '').trim();
              const cleanContent = rawContent
                .replace(/^[^—–\n]+(?:\(@[^\)]+\)|•|\bInstagram\b|\bLinkedIn\b|\bTwitter\b|\bReddit\b|\bFacebook\b)[^—–\n]*[—–]\s*/gi, '')
                .replace(/^[^—–\n]*\(@[^\)]+\)[^—–\n]*[—–]\s*/gi, '')
                .trim();
              
              const displayContent = cleanContent || rawContent;

              return (
                <div
                  key={post.id}
                  className="bg-white dark:bg-[#14141d] rounded-2xl p-4 sm:p-5 shadow-xs border border-slate-200/80 dark:border-white/10 flex flex-col justify-between transition-all duration-150 hover:shadow-md group"
                >
                  <div>
                    {/* Top Header Row: Platform Pill + Hot Pill on Left, Timestamp on Right */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        {getPlatformBadge(post.platform)}
                        {getIntentBadge(post)}
                      </div>
                      <span className="text-xs font-medium text-slate-400 dark:text-zinc-500">
                        {timeAgo(post.published_at)}
                      </span>
                    </div>

                    {/* Headline Section: Slim Greyish Vertical Bar + Bold Summary Title */}
                    <div className="flex items-stretch mb-2.5">
                      <div className="w-[3px] min-w-[3px] max-w-[3px] rounded-full bg-slate-300 dark:bg-zinc-600 shrink-0 mr-2.5 self-stretch my-0.5" />
                      <h3 className="text-base font-extrabold text-slate-900 dark:text-zinc-100 leading-snug tracking-tight line-clamp-2">
                        {post.summary || displayContent.split('\n')[0] || displayContent}
                      </h3>
                    </div>

                    {/* Body Snippet Paragraph */}
                    <p className="text-xs sm:text-sm font-normal text-slate-600 dark:text-zinc-400 leading-relaxed line-clamp-2 pl-0.5">
                      {post.summary ? displayContent : (displayContent.split('\n').slice(1).join(' ') || displayContent)}
                    </p>
                  </div>

                  {/* Horizontal Divider Line */}
                  <div className="my-3 border-t border-slate-100 dark:border-white/10" />

                  {/* Bottom Footer Row: Delete + View Post Buttons */}
                  <div className="flex items-center justify-end gap-2">
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={(e) => handleDelete(post.id, e)}
                        className="p-2 rounded-xl border border-slate-200 dark:border-white/10 text-slate-400 dark:text-zinc-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-slate-50 dark:hover:bg-white/5 transition"
                        title="Delete Post"
                      >
                        <Trash2 size={14} />
                      </button>

                      <a
                        href={post.post_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-4 py-2 bg-white/90 dark:bg-white text-slate-900 dark:text-zinc-950 font-bold text-xs rounded-xl shadow-xs hover:shadow-md transition-all hover:scale-105 active:scale-95 border border-slate-300/80 dark:border-white backdrop-blur-md hover:bg-white dark:hover:bg-zinc-100"
                      >
                        <span>View post</span>
                        <ExternalLink size={12} className="stroke-[2.5]" />
                      </a>
                    </div>
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
