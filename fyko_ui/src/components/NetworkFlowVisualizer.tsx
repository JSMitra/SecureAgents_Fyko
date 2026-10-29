import React from 'react';
import { ShieldCheck, Database, Layers, Send, RefreshCw } from 'lucide-react';
import { MissionStep } from '../types';

interface NetworkFlowVisualizerProps {
  activeStepId: number | null;
  steps: MissionStep[];
  annProgress: number;
}

export const NetworkFlowVisualizer: React.FC<NetworkFlowVisualizerProps> = ({
  activeStepId,
  steps,
  annProgress,
}) => {
  const isFykoActive = activeStepId !== null && [2, 3, 4].includes(activeStepId);
  const isA2ARsaActive = activeStepId === 7;
  const isA2AAesActive = activeStepId !== null && [8, 9, 10].includes(activeStepId);

  return (
    <div className="cyber-panel rounded-xl p-5 border border-slate-800 relative overflow-hidden">
      {/* Background Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b0a_1px,transparent_1px),linear-gradient(to_bottom,#1e293b0a_1px,transparent_1px)] bg-[size:16px_16px] pointer-events-none"></div>

      <div className="flex items-center justify-between mb-4 relative z-10">
        <h2 className="text-xs font-mono uppercase tracking-widest text-cyan-400 flex items-center gap-2">
          <Layers className="w-4 h-4" />
          Neural Key Generation & A2A Cryptographic Transmission Flow
        </h2>
        <span className="text-[11px] font-mono text-slate-400">
          STEP {activeStepId || 0} OF {steps.length}
        </span>
      </div>

      {/* Main Flow Canvas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
        {/* Node 1: Secret Plan Creator */}
        <div
          className={`p-4 rounded-xl border transition-all ${
            activeStepId !== null && [1, 2, 4, 5, 6, 7, 8, 10, 11].includes(activeStepId)
              ? 'bg-blue-950/30 border-blue-500/60 shadow-[0_0_20px_rgba(59,130,246,0.2)]'
              : 'bg-[#0f172a]/80 border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono font-bold text-blue-400 flex items-center gap-1.5">
              <span>🤵</span> CREATOR (Port 9001)
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
              ORIGIN
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-3">
            Requests ANN model, derives dynamic AES-256 key, encrypts query, and logs interaction.
          </p>
          <div className="text-[11px] font-mono bg-black/40 p-2 rounded border border-slate-800/80 space-y-1">
            <div className="text-slate-400 flex justify-between">
              <span>ULID State:</span>
              <span className="text-cyan-300 font-bold">{steps[1]?.payloadSnippet || 'READY'}</span>
            </div>
            <div className="text-slate-400 flex justify-between">
              <span>AES Key:</span>
              <span className="text-emerald-400">{steps[4]?.payloadSnippet || 'UNINITIALIZED'}</span>
            </div>
          </div>
        </div>

        {/* Center Node: Fyko Server + RabbitMQ + Workers */}
        <div
          className={`p-4 rounded-xl border transition-all ${
            isFykoActive
              ? 'bg-amber-950/30 border-amber-500/60 shadow-[0_0_20px_rgba(245,158,11,0.2)]'
              : 'bg-[#0f172a]/80 border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono font-bold text-amber-400 flex items-center gap-1.5">
              <Database className="w-4 h-4" /> FYKO SERVER & WORKERS
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
              ORCHESTRATOR
            </span>
          </div>

          <p className="text-xs text-slate-400 mb-2">
            FastAPI + PostgreSQL (ULID pending) ➔ RabbitMQ ➔ 2× ANN_Generator workers ➔ MongoDB GridFS.
          </p>

          {/* Progress bar during training */}
          <div className="mt-2">
            <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
              <span>ANN Model Training (Keras):</span>
              <span className="text-amber-300 font-bold">{annProgress}%</span>
            </div>
            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
              <div
                className="bg-gradient-to-r from-amber-500 to-emerald-400 h-full transition-all duration-300"
                style={{ width: `${annProgress}%` }}
              ></div>
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between text-[10px] font-mono text-slate-500 border-t border-slate-800/80 pt-2">
            <span>Prefetch: 1 (Exclusive)</span>
            <span>Queue: Non-Durable</span>
          </div>
        </div>

        {/* Node 3: Secret Plan Reviewer */}
        <div
          className={`p-4 rounded-xl border transition-all ${
            activeStepId !== null && [7, 8, 9, 10].includes(activeStepId)
              ? 'bg-purple-950/30 border-purple-500/60 shadow-[0_0_20px_rgba(168,85,247,0.2)]'
              : 'bg-[#0f172a]/80 border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono font-bold text-purple-400 flex items-center gap-1.5">
              <span>🕵️</span> REVIEWER (Port 9002)
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950 text-purple-400 border border-purple-800">
              TARGET
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-3">
            Decrypts RSA key-share, fetches same ANN model, decrypts query, calls Gemini, re-encrypts.
          </p>
          <div className="text-[11px] font-mono bg-black/40 p-2 rounded border border-slate-800/80 space-y-1">
            <div className="text-slate-400 flex justify-between">
              <span>A2A Endpoint:</span>
              <span className="text-purple-300 font-bold">/a2a/tasks/send</span>
            </div>
            <div className="text-slate-400 flex justify-between">
              <span>Status:</span>
              <span className={activeStepId === 9 ? 'text-cyan-400 animate-pulse' : 'text-slate-400'}>
                {activeStepId === 9 ? 'LLM EVALUATING...' : 'SYNCHRONIZED'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Transmission Pipeline Indicator */}
      <div className="mt-5 p-3 rounded-lg bg-black/50 border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping"></span>
          <span className="text-slate-400">ACTIVE PACKET:</span>
          {isFykoActive ? (
            <span className="text-amber-400 font-bold flex items-center gap-1">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ANN GENERATION PIPELINE (HTTP ➔ AMQP ➔ GridFS)
            </span>
          ) : isA2ARsaActive ? (
            <span className="text-rose-400 font-bold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              RSA-OAEP(2048) ENCRYPTED KEY-SHARE [CREATOR ➔ REVIEWER]
            </span>
          ) : isA2AAesActive ? (
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              <Send className="w-3.5 h-3.5" />
              ANN-AES-256 ENCRYPTED A2A MISSION PAYLOAD
            </span>
          ) : (
            <span className="text-slate-500">IDLE (AWAITING USER INSTRUCTION)</span>
          )}
        </div>

        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400"></span> ANN Broker
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-400"></span> RSA-2048
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span> ANN-AES-256
          </span>
        </div>
      </div>
    </div>
  );
};
