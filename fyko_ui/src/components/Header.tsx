import React, { useState, useEffect } from 'react';
import { Shield, Radio, Terminal, Cpu, Database } from 'lucide-react';
import { ServiceHealth } from '../types';

interface HeaderProps {
  health: ServiceHealth;
  refreshHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, refreshHealth }) => {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      setTimeStr(new Date().toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: 'online' | 'offline' | 'checking') => {
    if (status === 'online') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          ONLINE
        </span>
      );
    }
    if (status === 'checking') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
          POLLING
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
        STANDBY
      </span>
    );
  };

  return (
    <header className="border-b border-cardBorder bg-[#0b101c]/90 backdrop-blur sticky top-0 z-50 px-4 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand and Mission Title */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
            <Shield className="w-6 h-6 animate-pulse" />
            <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping"></div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-wider text-slate-100 flex items-center gap-2">
                FYKO <span className="text-cyan-400">SECURE AGENTS</span>
              </h1>
              <span className="text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800">
                A2A ENCRYPTED
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Thesis: Generating AES Keys using Artificial Neural Networks (Mitra J.S.)
            </p>
          </div>
        </div>

        {/* Live Cluster Health Indicators */}
        <div className="flex flex-wrap items-center gap-3 bg-[#0d1424] px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={refreshHealth}
            title="Click to re-ping services"
            className="flex items-center gap-1.5 text-slate-400 hover:text-cyan-400 transition-colors pr-2 border-r border-slate-800"
          >
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-mono">CLUSTER:</span>
          </button>

          <div className="flex items-center gap-1.5" title="Fyko FastAPI Server (Port 8000)">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-300">Fyko_Server</span>
            {getStatusBadge(health.fykoServer)}
          </div>

          <div className="flex items-center gap-1.5" title="Secret Plan Creator (Port 9001)">
            <Terminal className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-slate-300">Creator</span>
            {getStatusBadge(health.secretPlanCreator)}
          </div>

          <div className="flex items-center gap-1.5" title="Secret Plan Reviewer (Port 9002)">
            <Terminal className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-slate-300">Reviewer</span>
            {getStatusBadge(health.secretPlanReviewer)}
          </div>

          <div className="flex items-center gap-1.5" title="ANN Generator StatefulSet (2 Pods)">
            <Database className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-300">Workers (×2)</span>
            {getStatusBadge(health.workerPool)}
          </div>
        </div>

        {/* UTC Clock */}
        <div className="hidden lg:flex items-center gap-2 font-mono text-xs text-slate-400 bg-black/40 px-3 py-1 rounded border border-slate-800">
          <span className="w-2 h-2 rounded-full bg-cyan-400/80"></span>
          <span>{timeStr || 'SYNCHRONIZING UTC...'}</span>
        </div>
      </div>
    </header>
  );
};

