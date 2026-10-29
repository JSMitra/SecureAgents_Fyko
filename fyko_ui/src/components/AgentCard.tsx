import React from 'react';
import { KeyRound, Lock, Cpu, Sparkles } from 'lucide-react';

interface AgentCardProps {
  type: 'creator' | 'reviewer';
  isActive: boolean;
  activeAction?: string;
  keysInfo?: {
    rsaPublicFingerprint?: string;
    annModelUlid?: string;
    aesKeyStatus?: string;
  };
}

export const AgentCard: React.FC<AgentCardProps> = ({
  type,
  isActive,
  activeAction,
  keysInfo,
}) => {
  const isCreator = type === 'creator';

  const roleName = isCreator ? 'Secret Plan Creator' : 'Secret Plan Reviewer';
  const roleSub = isCreator
    ? 'Intelligence Operative (Strategic Plan Formulation)'
    : 'Reviewer Operative (Plan Evaluation & Risk Assessment)';
  const port = isCreator ? '9001' : '9002';

  return (
    <div
      className={`relative rounded-xl p-5 border transition-all duration-300 ${
        isActive
          ? isCreator
            ? 'bg-blue-950/20 border-blue-500/60 shadow-[0_0_30px_rgba(59,130,246,0.15)]'
            : 'bg-purple-950/20 border-purple-500/60 shadow-[0_0_30px_rgba(168,85,247,0.15)]'
          : 'bg-[#0f172a]/70 border-slate-800'
      }`}
    >
      {/* Top Bar */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`w-12 h-12 rounded-lg flex items-center justify-center text-2xl border ${
              isCreator
                ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                : 'bg-purple-500/10 border-purple-500/30 text-purple-400'
            }`}
          >
            {isCreator ? '🤵' : '🕵️'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-100 text-sm tracking-wide">{roleName}</h3>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase font-semibold ${
                  isActive
                    ? isCreator
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse'
                      : 'bg-purple-500/20 text-purple-300 border border-purple-500/40 animate-pulse'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {isActive ? 'ACTIVE TRANSMISSION' : 'STANDBY'}
              </span>
            </div>
            <p className="text-xs text-slate-400">{roleSub}</p>
          </div>
        </div>

        <div className="text-right font-mono text-[11px] text-slate-500">
          <div>PORT: :{port}</div>
          <div>PROTOCOL: A2A</div>
        </div>
      </div>

      {/* Real-time Operative State */}
      <div className="mb-4 bg-black/40 rounded-lg p-2.5 border border-slate-800/80">
        <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
          <span>OPERATIONAL STATUS</span>
          <span className="flex items-center gap-1 text-cyan-400">
            <Sparkles className="w-3 h-3" /> Gemini 2.0 Flash
          </span>
        </div>
        <div className="text-xs font-mono text-slate-200 truncate flex items-center gap-2">
          {isActive ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span className="text-cyan-300 font-semibold">{activeAction || 'Executing mission workflow...'}</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-slate-600"></span>
              <span className="text-slate-400">Ready for incoming instructions</span>
            </>
          )}
        </div>
      </div>

      {/* Cryptographic Arsenal */}
      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
        <div className="bg-[#111927] p-2 rounded border border-slate-800">
          <div className="flex items-center gap-1 text-slate-400 text-[10px] mb-1">
            <KeyRound className="w-3 h-3 text-amber-400" />
            <span>RSA-2048 (PostgreSQL)</span>
          </div>
          <div className="text-slate-300 truncate" title="Public key registered in agent_keys table">
            {keysInfo?.rsaPublicFingerprint || (isCreator ? 'SHA256: 7d:1a...creator' : 'SHA256: 3c:9f...reviewer')}
          </div>
        </div>

        <div className="bg-[#111927] p-2 rounded border border-slate-800">
          <div className="flex items-center gap-1 text-slate-400 text-[10px] mb-1">
            <Lock className="w-3 h-3 text-emerald-400" />
            <span>ANN AES-256 KEY</span>
          </div>
          <div className="text-slate-300 truncate" title="Synchronized via FYKO model derivation">
            {keysInfo?.aesKeyStatus || (isActive ? 'DYNAMIC KEY DERIVED' : 'PENDING ACTIVATION')}
          </div>
        </div>
      </div>

      {/* Model ULID indicator */}
      <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <span className="flex items-center gap-1">
          <Cpu className="w-3 h-3 text-cyan-400" />
          <span>MODEL ULID:</span>
        </span>
        <span className="text-cyan-300 font-medium truncate max-w-[150px]">
          {keysInfo?.annModelUlid || 'AWAITING_REQUEST'}
        </span>
      </div>
    </div>
  );
};
