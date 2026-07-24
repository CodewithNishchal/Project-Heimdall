import React, { useEffect, useState, useMemo } from 'react';
import { Trash2, Search, RefreshCw, MessageSquare, ExternalLink } from 'lucide-react';
import { fetchSocialPosts, deleteSocialPost, triggerSocialSweep } from '../lib/api';
import type { SocialPost } from '../types/lead';

const TABS = ['All', 'Reddit', 'Yelp', 'X', 'Facebook', 'Instagram', 'LinkedIn', 'Quora', 'Google', 'Discord', 'Slack', 'Skool', 'Threads'];

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

    if (plat === 'yelp') {
      bg = '#991b1b';
      label = 'YELP';
    } else if (plat === 'x' || plat === 'twitter') {
      bg = '#27272a';
      label = 'X';
    } else if (plat === 'reddit') {
      bg = '#c2410c';
      label = 'REDDIT';
    } else if (plat === 'instagram') {
      bg = '#831843';
      label = 'INSTAGRAM';
    } else if (plat === 'facebook') {
      bg = '#1e40af';
      label = 'FACEBOOK';
    } else if (plat === 'linkedin') {
      bg = '#0369a1';
      label = 'LINKEDIN';
    } else if (plat === 'quora') {
      bg = '#b92b27';
      label = 'QUORA';
    } else if (plat === 'google') {
      bg = '#1d4ed8';
      label = 'GOOGLE Q&A';
    } else if (plat === 'discord') {
      bg = '#4338ca';
      label = 'DISCORD';
    } else if (plat === 'slack') {
      bg = '#581c87';
      label = 'SLACK';
    } else if (plat === 'skool') {
      bg = '#1d4ed8';
      label = 'SKOOL';
    } else if (plat === 'threads') {
      bg = '#09090b';
      label = 'THREADS';
    }


    return (
      <span
        style={{ backgroundColor: bg, color: text }}
        className="text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider shadow-sm"
      >
        {label}
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full space-y-6">
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

      {/* Tabs Row */}
      <div className="flex gap-2.5 overflow-x-auto pb-1 scrollbar-hide">
        {TABS.map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold border transition-all whitespace-nowrap shadow-sm ${
                isActive
                  ? 'bg-[var(--nexa-accent)] text-zinc-950 border-[var(--nexa-accent)] font-extrabold'
                  : 'border-nexa-border bg-nexa-surface text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* Content Feed */}
      <div className="flex-1 overflow-y-auto pr-1 pb-6 space-y-4">
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredPosts.map((post) => (
              <div
                key={post.id}
                className="nexa-card group relative p-5 shadow-xl flex flex-col justify-between transition-all"
              >
                {/* Top Badge & Time */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    {getPlatformBadge(post.platform)}
                  </div>

                  {/* Company & Handle Header */}
                  <div className="mb-2">
                    <h3 className="text-sm font-bold text-zinc-100 inline-block mr-2">
                      {post.company_name || post.author_name || 'Prospect Team'}
                    </h3>
                    <span className="text-xs text-zinc-400 font-normal">
                      @{post.author_handle || 'growth_lead'}
                    </span>
                  </div>

                  {/* Body Content */}
                  <p className="text-xs text-zinc-300 leading-relaxed font-normal mb-4 line-clamp-4">
                    {post.content}
                  </p>
                </div>

                {/* Footer Section */}
                <div className="border-t border-white/10 pt-3.5 mt-2 flex items-center justify-between">
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-zinc-500 font-semibold block mb-0.5">
                      MATCHED KEYWORD
                    </span>
                    <span style={{ color: 'var(--nexa-accent)' }} className="text-xs font-semibold">
                      {post.keyword_matched || 'marketing agency'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <a
                      href={post.post_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 text-zinc-200 text-xs font-medium rounded-lg border border-white/10 transition-all shadow-sm"
                    >
                      View Post
                      <ExternalLink size={12} />
                    </a>
                    <button
                      onClick={(e) => handleDelete(post.id, e)}
                      className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-white/10 rounded-lg transition-all"
                      title="Delete Post"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
