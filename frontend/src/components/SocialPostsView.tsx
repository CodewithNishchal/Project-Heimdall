import React, { useEffect, useState, useMemo } from 'react';
import { Trash2, Search, RefreshCw, MessageSquare, ExternalLink } from 'lucide-react';
import { fetchSocialPosts, deleteSocialPost, triggerSocialSweep } from '../lib/api';
import type { SocialPost } from '../types/lead';
const TABS = ['All', 'Reddit', 'X', 'Facebook', 'Instagram', 'LinkedIn', 'Google', 'Skool', 'Threads'];

function timeAgo(dateString: string) {
  if (!dateString) return '1h ago';
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (isNaN(seconds) || seconds < 60) return 'Just now';
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

  const loadPosts = async () => {
    setLoading(true);
    try {
      const data = await fetchSocialPosts(activeTab === 'All' ? undefined : activeTab.toLowerCase());
      setPosts(data);
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
    try {
      await triggerSocialSweep();
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
    if (!searchQuery.trim()) return posts;
    const q = searchQuery.toLowerCase();
    return posts.filter(
      (p) =>
        p.content.toLowerCase().includes(q) ||
        p.company_name?.toLowerCase().includes(q) ||
        p.author_name?.toLowerCase().includes(q) ||
        p.author_handle?.toLowerCase().includes(q) ||
        p.keyword_matched?.toLowerCase().includes(q)
    );
  }, [posts, searchQuery]);

  const getPlatformBadge = (platform: string) => {
    const plat = platform.toLowerCase();
    let bg = '#27272a';
    let text = '#ffffff';
    let label = platform.toUpperCase();

    if (plat === 'x' || plat === 'twitter') {
      bg = '#27272a';
      text = '#ffffff';
      label = 'X';
    } else if (plat === 'reddit') {
      bg = '#7c2d12';
      text = '#ffedd5';
      label = 'Reddit';
    } else if (plat === 'instagram') {
      bg = '#701a75';
      text = '#fae8ff';
      label = 'Instagram';
    } else if (plat === 'facebook') {
      bg = '#1e3a8a';
      text = '#dbeafe';
      label = 'Facebook';
    } else if (plat === 'linkedin') {
      bg = '#1e3a8a';
      text = '#dbeafe';
      label = 'LinkedIn';
    } else if (plat === 'google') {
      bg = '#14532d';
      text = '#dcfce7';
      label = 'Google Q&A';
    } else if (plat === 'skool') {
      bg = '#1e3a8a';
      text = '#dbeafe';
      label = 'Skool';
    } else if (plat === 'threads') {
      bg = '#18181b';
      text = '#ffffff';
      label = 'Threads';
    } else if (plat === 'yelp') {
      bg = '#7f1d1d';
      text = '#ffe4e6';
      label = 'Yelp';
    }

    return (
      <span
        style={{ backgroundColor: bg, color: text }}
        className="text-[11px] font-bold px-2.5 py-0.5 rounded-md shadow-sm"
      >
        {label}
      </span>
    );
  };

  const getIntentBadge = (post: SocialPost) => {
    const isHot = (post.company_name && post.company_name !== 'Prospect Team') || 
                  (post.keyword_matched && (post.keyword_matched.includes('agency') || post.keyword_matched.includes('hiring') || post.keyword_matched.includes('recommend')));
    
    if (isHot) {
      return (
        <span 
          style={{ backgroundColor: 'rgba(6, 78, 59, 0.85)', color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.4)' }}
          className="text-[11px] font-bold px-2 py-0.5 rounded-md border flex items-center gap-1 shadow-sm"
        >
          <span className="text-[10px]">☐</span> Hot
        </span>
      );
    }
    return (
      <span 
        style={{ backgroundColor: 'rgba(120, 53, 15, 0.85)', color: '#fbbf24', borderColor: 'rgba(217, 119, 6, 0.4)' }}
        className="text-[11px] font-bold px-2 py-0.5 rounded-md border flex items-center gap-1 shadow-sm"
      >
        Warm
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full space-y-5">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center">
          <div
            style={{
              background: 'radial-gradient(circle at 30% 30%, #F5C563 0%, #E5A93C 55%, #B37E25 100%)',
              borderRadius: '50%',
              width: '42px',
              height: '42px',
              minWidth: '42px',
              minHeight: '42px',
              maxWidth: '42px',
              maxHeight: '42px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              marginRight: '1.25rem',
            }}
            className="shadow-md shadow-[#E5A93C]/25"
          >
            <MessageSquare size={19} style={{ color: '#121215' }} className="stroke-[2.3]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">Social Media Signals</h1>
            <p className="text-xs text-zinc-400 font-medium">Discover active intent posts from Scrape Creators</p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search
              style={{ left: '0.875rem' }}
              className="absolute top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none"
              size={15}
            />
            <input
              type="text"
              placeholder="Search keywords or posts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full border border-nexa-border bg-nexa-surface rounded-full py-2.5 pl-10 pr-4 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-[var(--nexa-accent)] transition-all"
            />
          </div>

          <button
            onClick={handleFetch}
            disabled={fetching}
            style={{ backgroundColor: 'var(--nexa-accent)', color: '#000000' }}
            className="flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-xl hover:opacity-90 transition-all shadow-md disabled:opacity-50 whitespace-nowrap"
          >
            {fetching ? <RefreshCw className="animate-spin" size={14} /> : <RefreshCw size={14} />}
            Fetch Intent Posts
          </button>
        </div>
      </div>

      {/* Summary KPI Pills Bar */}
      <div className="flex items-center gap-2.5 overflow-x-auto pb-1 text-xs">
        <span className="nexa-card text-zinc-300 px-3.5 py-1.5 rounded-full font-medium border border-nexa-border shadow-sm flex items-center gap-1.5">
          <strong className="font-extrabold text-zinc-100">{filteredPosts.length}</strong> threads found
        </span>
        <span className="nexa-card text-zinc-300 px-3.5 py-1.5 rounded-full font-medium border border-nexa-border shadow-sm flex items-center gap-1.5">
          <strong className="font-extrabold text-zinc-100">{filteredPosts.filter(p => (p.keyword_matched && (p.keyword_matched.includes('agency') || p.keyword_matched.includes('hiring')))).length}</strong> hot leads
        </span>
        <span className="nexa-card text-zinc-300 px-3.5 py-1.5 rounded-full font-medium border border-nexa-border shadow-sm flex items-center gap-1.5">
          <strong className="font-extrabold text-zinc-100">{Math.max(0, filteredPosts.length - filteredPosts.filter(p => (p.keyword_matched && (p.keyword_matched.includes('agency') || p.keyword_matched.includes('hiring')))).length)}</strong> warm
        </span>
        <span className="nexa-card text-zinc-400 px-3.5 py-1.5 rounded-full font-medium border border-nexa-border shadow-sm">
          Last fetched: recently
        </span>
      </div>

      {/* Tabs Row */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {TABS.map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold border transition-all whitespace-nowrap shadow-sm ${
                isActive
                  ? 'bg-[var(--nexa-accent)] text-zinc-950 border-[var(--nexa-accent)] font-extrabold'
                  : 'border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-100'
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* Content Feed — Row-Based Design */}
      <div className="flex-1 overflow-y-auto pr-1 pb-6">
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
          <div className="flex flex-col space-y-3.5">
            {filteredPosts.map((post) => {
              const tags = (post.keyword_matched || 'marketing agency')
                .split(',')
                .flatMap(k => k.trim().split(' '))
                .filter(Boolean)
                .slice(0, 4);

              const mainHeadline = post.company_name 
                ? `${post.company_name} — "${post.content.length > 90 ? post.content.slice(0, 90).trim() + '...' : post.content}"`
                : post.content;

              const subText = post.content.length > 90 && post.company_name
                ? post.content
                : `Verified intent post by @${post.author_handle || post.author_name || 'growth_lead'} · Matched keyword "${post.keyword_matched || 'agency'}"`;

              return (
                <div
                  key={post.id}
                  className="nexa-card rounded-2xl p-5 shadow-lg flex flex-col justify-between transition-all group border border-nexa-border hover:border-nexa-border-strong"
                >
                  {/* Top Header Row: Platform Badge + Intent Tag on Left, Time & Author on Right */}
                  <div className="flex items-center justify-between mb-2.5">
                    <div className="flex items-center gap-2">
                      {getPlatformBadge(post.platform)}
                      {getIntentBadge(post)}
                    </div>
                    <span className="text-xs text-zinc-400 font-medium">
                      {timeAgo(post.published_at)} {post.author_handle ? `· @${post.author_handle}` : ''}
                    </span>
                  </div>

                  {/* Body Content: Main Title & Subtitle */}
                  <div className="mb-3.5">
                    <h3 className="text-base font-bold text-zinc-100 mb-1 leading-snug tracking-tight">
                      {mainHeadline}
                    </h3>
                    <p className="text-xs text-zinc-300 leading-relaxed font-normal line-clamp-2">
                      {subText}
                    </p>
                  </div>

                  {/* Bottom Footer Row: Keywords on Left, View Thread/Post Button on Right */}
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex flex-wrap gap-1.5 items-center">
                      {tags.map((tag, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-[var(--nexa-indigo-dim)] text-[var(--nexa-indigo)] border border-indigo-500/30"
                        >
                          {tag.toLowerCase()}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleDelete(post.id, e)}
                        className="p-1.5 text-zinc-400 hover:text-rose-500 hover:bg-white/10 rounded-lg transition-all"
                        title="Delete Post"
                      >
                        <Trash2 size={14} />
                      </button>

                      <a
                        href={post.post_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-4 py-1.5 bg-nexa-surface hover:bg-nexa-card-hover text-zinc-100 text-xs font-semibold rounded-xl border border-nexa-border transition-all shadow-sm"
                      >
                        {post.platform.toLowerCase() === 'reddit' ? 'View thread' : 'View post'}
                        <span className="text-sm font-sans leading-none">↗</span>
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
