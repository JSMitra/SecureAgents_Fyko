import React from 'react';
import { Terminal, Shield, Activity } from 'lucide-react';

interface TelemetryLogProps {
  logs: { id: string; time: string; message: string; type: 'info' | 'crypto' | 'network' | 'success' }[];
}

export const TelemetryLog: React.FC<TelemetryLogProps> = ({ logs }) => {
  const getBadge = (type: string) => {
    switch (type) {
      case 'crypto':
        return <span className="text-emerald-400 font-bold">[CRYPTO]</span>;
      case 'network':
        return <span className="text-cyan-400 font-bold">[A2A-NET]</span>;
      case 'success':
        return <span className="text-green-400 font-bold">[SUCCESS]</span>;
      default:
        return <span className="text-slate-500 font-bold">[SYSTEM]</span>;
    }
  };

  return (
    <div className="cyber-panel rounded-xl p-4 border border-slate-800 flex flex-col h-[340px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-2">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          Operative Telemetry & Protocol Log
        </h3>
        <span className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400">
          <Activity className="w-3 h-3 animate-pulse" />
          LIVE EVENTSTREAM
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 font-mono text-xs pr-2 select-text">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-600 text-xs">
            <Shield className="w-8 h-8 mb-2 opacity-30" />
            <span>Awaiting mission activation... Click "Initiate Agent Interaction"</span>
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className={`p-1.5 rounded transition-colors ${
                log.type === 'crypto'
                  ? 'bg-emerald-950/20 text-emerald-300 border-l-2 border-emerald-500'
                  : log.type === 'network'
                  ? 'bg-cyan-950/20 text-cyan-200 border-l-2 border-cyan-500'
                  : log.type === 'success'
                  ? 'bg-green-950/30 text-green-200 border-l-2 border-green-400 font-semibold'
                  : 'bg-black/20 text-slate-300'
              }`}
            >
              <div className="flex items-start gap-2">
                <span className="text-slate-500 text-[10px] whitespace-nowrap mt-0.5">{log.time}</span>
                <span className="text-[11px] whitespace-nowrap">{getBadge(log.type)}</span>
                <span className="flex-1 break-all leading-relaxed">{log.message}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
