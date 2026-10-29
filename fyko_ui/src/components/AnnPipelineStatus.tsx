import React from 'react';
import { CheckCircle2, Clock } from 'lucide-react';
import { MissionStep } from '../types';

interface AnnPipelineStatusProps {
  steps: MissionStep[];
  activeStepId: number | null;
}

export const AnnPipelineStatus: React.FC<AnnPipelineStatusProps> = ({ steps, activeStepId }) => {
  return (
    <div className="cyber-panel rounded-xl p-5 border border-slate-800">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300">
          Cryptographic Handshake & Neural Pipeline Stepper
        </h3>
        <span className="text-[10px] font-mono text-cyan-400">11-STEP A2A SEQUENCE</span>
      </div>

      <div className="space-y-2">
        {steps.map((step) => {
          const isActive = activeStepId === step.id;
          const isDone = step.status === 'completed';

          return (
            <div
              key={step.id}
              className={`p-2.5 rounded-lg border text-xs font-mono transition-all flex items-center justify-between gap-3 ${
                isActive
                  ? 'bg-cyan-950/30 border-cyan-500/60 shadow-[0_0_15px_rgba(6,182,212,0.15)] text-cyan-200'
                  : isDone
                  ? 'bg-slate-900/60 border-slate-800 text-slate-300'
                  : 'bg-black/20 border-slate-900 text-slate-500 opacity-60'
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex-shrink-0">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : isActive ? (
                    <span className="relative flex h-3.5 w-3.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-cyan-500"></span>
                    </span>
                  ) : (
                    <Clock className="w-4 h-4 text-slate-600" />
                  )}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[11px] text-slate-400">#{step.id}</span>
                    <span className="font-semibold text-slate-100 truncate">{step.label}</span>
                  </div>
                  <div className="text-[10px] text-slate-400 truncate mt-0.5">{step.description}</div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {step.protocol}
                </span>

                {step.payloadSnippet && (
                  <span className="hidden sm:inline-block text-[10px] px-1.5 py-0.5 rounded bg-black/60 text-emerald-400 border border-emerald-900/50 truncate max-w-[140px]">
                    {step.payloadSnippet}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
