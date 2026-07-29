import { Search, Sparkles, FileText } from 'lucide-react';
import { motion } from 'framer-motion';

const BLURRED_NAMES = [
  'Acme Global Dynamics Inc.',
  'TechCorp Synthetics LLC',
  'Vortex Intelligence Systems',
  'OmniData AI Technologies',
  'Hyperion Cybernetics Corp',
  'Starlight Cloud Platforms',
  'Nexus BioTech Enterprise',
  'Apex Logic & Analytics',
  'Quantum Scale Networks',
  'Cipher Core Software',
  'Aetherial Data Labs',
  'Vector Prime Automation',
];

export default function DocumentMagnifierScan() {
  // Duplicate array to ensure seamless infinite looping animation
  const doubledNames = [...BLURRED_NAMES, ...BLURRED_NAMES];

  return (
    <div className="flex flex-col items-center justify-center p-8 sm:p-12 my-auto w-full min-h-[420px]">
      {/* Animation Canvas */}
      <div className="relative flex items-center justify-center w-72 h-80 sm:w-80 sm:h-96">
        {/* Pulsing ambient glow aura */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-emerald-500/20 via-teal-500/10 to-amber-500/15 blur-2xl animate-pulse" />

        {/* 1. CENTRAL DOCUMENT CARD */}
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="relative w-56 h-72 sm:w-64 sm:h-80 rounded-2xl border border-emerald-500/30 bg-slate-900/90 dark:bg-zinc-950/90 backdrop-blur-md shadow-2xl p-4 flex flex-col justify-between overflow-hidden z-10"
        >
          {/* Top Document Header */}
          <div className="flex items-center justify-between pb-3 border-b border-emerald-500/20 shrink-0">
            <div className="flex items-center gap-2">
              <FileText size={16} className="text-emerald-400" />
              <span className="text-[11px] font-bold tracking-wider text-slate-300 dark:text-zinc-300 uppercase font-mono">
                Discovery_Report.pdf
              </span>
            </div>
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
          </div>

          {/* Scrolling Blurred Company Names Section */}
          <div className="relative flex-1 my-3 overflow-hidden rounded-lg bg-slate-950/60 dark:bg-black/60 border border-slate-800 dark:border-zinc-800/80 p-2.5">
            {/* Top & Bottom gradient mask for smooth fade out */}
            <div className="absolute inset-x-0 top-0 h-6 bg-gradient-to-b from-slate-950 dark:from-black to-transparent z-10 pointer-events-none" />
            <div className="absolute inset-x-0 bottom-0 h-6 bg-gradient-to-t from-slate-950 dark:from-black to-transparent z-10 pointer-events-none" />

            {/* Vertical Infinite Scroll Track */}
            <div className="animate-scroll-blurred flex flex-col gap-2">
              {doubledNames.map((name, idx) => (
                <div
                  key={`${name}-${idx}`}
                  className="flex items-center justify-between py-1 px-2 rounded bg-emerald-950/20 border border-emerald-500/10 select-none"
                >
                  <span
                    className="text-xs font-semibold text-emerald-200/80 tracking-wide font-mono blur-[3.5px] transition-all"
                    style={{ textShadow: '0 0 8px rgba(16, 185, 129, 0.5)' }}
                  >
                    {name}
                  </span>
                  <div className="w-12 h-2 rounded bg-emerald-500/30 blur-[2px]" />
                </div>
              ))}
            </div>
          </div>

          {/* Document Footer Bar */}
          <div className="pt-2 border-t border-emerald-500/20 flex items-center justify-between shrink-0 text-[10px] font-mono text-slate-400 dark:text-zinc-400">
            <span className="flex items-center gap-1">
              <Sparkles size={11} className="text-emerald-400" /> Multi-Source Intent
            </span>
            <span className="text-emerald-400 font-bold">LIVE CRAWL</span>
          </div>
        </motion.div>

        {/* 2. INFINITELY ORBITING MAGNIFYING GLASS */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
          <div className="w-full h-full animate-orbit-magnifier relative flex items-center justify-center">
            {/* The magnifying glass is positioned at radius from center */}
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 flex items-center justify-center">
              <div className="relative flex items-center justify-center w-14 h-14 rounded-full bg-emerald-500/20 border-2 border-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.8)] backdrop-blur-md">
                <Search size={26} className="text-emerald-300 stroke-[2.5] animate-pulse" />
                {/* Micro glow dot */}
                <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 animate-ping" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Status Text & Indicator below animation */}
      <div className="mt-8 flex flex-col items-center gap-2 text-center">
        <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 text-xs font-bold font-mono shadow-md">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span>Intent Discovery Pipeline Active</span>
        </div>
        <p className="text-xs text-slate-400 dark:text-zinc-400 font-medium max-w-sm">
          Searching Google SERPs, Reddit, X, LinkedIn & Apollo APIs for intent signals...
        </p>
      </div>
    </div>
  );
}
