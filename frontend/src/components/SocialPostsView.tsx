import React, { useEffect, useState, useMemo } from 'react';
import { Trash2, Search, RefreshCw, MessageSquare, ExternalLink } from 'lucide-react';
import { fetchSocialPosts, deleteSocialPost, triggerSocialSweep } from '../lib/api';
import type { SocialPost } from '../types/lead';

const TABS = ['All', 'Reddit', 'Yelp', 'X', 'Facebook', 'Instagram', 'LinkedIn'];

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
            <h1 className="text-2xl font-bold text-white tracking-tight">Social Media Signals</h1>
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
              style={{
                backgroundColor: '#141417',
                borderColor: '#27272A',
                paddingLeft: '2.75rem',
                paddingRight: '1rem',
              }}
              className="w-full border rounded-full py-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#E5A93C] transition-all"
            />
          </div>

          <button
            onClick={handleFetch}
            disabled={fetching}
            style={{ backgroundColor: '#E5A93C', color: '#000000' }}
            className="flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl hover:opacity-90 transition-all shadow-md disabled:opacity-50 whitespace-nowrap"
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
              style={{
                backgroundColor: isActive ? '#E5A93C' : '#18181B',
                color: isActive ? '#000000' : '#A1A1AA',
                borderColor: isActive ? '#E5A93C' : '#27272A',
              }}
              className="px-4 py-1.5 rounded-full text-xs font-semibold border transition-all whitespace-nowrap shadow-sm"
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
            <RefreshCw className="animate-spin text-[#E5A93C]" size={28} />
          </div>
        ) : filteredPosts.length === 0 ? (
          <div
            style={{ backgroundColor: 'rgba(18, 18, 21, 0.8)', borderColor: '#27272A' }}
            className="flex flex-col justify-center items-center h-60 border rounded-2xl backdrop-blur-sm"
          >
            <MessageSquare size={36} className="text-zinc-600 mb-3" />
            <p className="text-zinc-400 text-sm font-medium">No intent posts discovered for this category.</p>
            <p className="text-zinc-600 text-xs mt-1">Try clicking "Fetch Intent Posts" to run a fresh sweep.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredPosts.map((post) => (
              <div
                key={post.id}
                style={{ backgroundColor: '#121215', borderColor: '#27272A' }}
                className="group relative border hover:border-zinc-600 rounded-xl p-5 shadow-xl flex flex-col justify-between transition-all"
              >
                {/* Top Badge & Time */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    {getPlatformBadge(post.platform)}
                    <span className="text-xs text-zinc-400 font-medium">{timeAgo(post.published_at)}</span>
                  </div>

                  {/* Company & Handle Header */}
                  <div className="mb-2">
                    <h3 className="text-sm font-bold text-white inline-block mr-2">
                      {post.company_name || post.author_name || 'Prospect Team'}
                    </h3>
                    <span className="text-xs text-zinc-500 font-normal">
                      @{post.author_handle || 'growth_lead'}
                    </span>
                  </div>

                  {/* Body Content */}
                  <p className="text-xs text-zinc-300 leading-relaxed font-normal mb-4 line-clamp-4">
                    {post.content}
                  </p>
                </div>

                {/* Footer Section */}
                <div style={{ borderColor: 'rgba(39, 39, 42, 0.8)' }} className="border-t pt-3.5 mt-2 flex items-center justify-between">
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-zinc-500 font-semibold block mb-0.5">
                      MATCHED KEYWORD
                    </span>
                    <span style={{ color: '#E5A93C' }} className="text-xs font-semibold">
                      {post.keyword_matched || 'marketing agency'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <a
                      href={post.post_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ backgroundColor: '#1C1C20', borderColor: '#3F3F46' }}
                      className="flex items-center gap-1.5 px-3 py-1.5 hover:bg-[#27272A] text-zinc-200 text-xs font-medium rounded-lg border transition-all shadow-sm"
                    >
                      View Post
                      <ExternalLink size={12} />
                    </a>
                    <button
                      onClick={(e) => handleDelete(post.id, e)}
                      className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-zinc-800 rounded-lg transition-all"
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
