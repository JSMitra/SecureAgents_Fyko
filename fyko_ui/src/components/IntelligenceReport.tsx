import React, { useState } from 'react';
import { Copy, Check, ShieldCheck, Database, Cpu } from 'lucide-react';
import { MissionResult } from '../types';

interface IntelligenceReportProps {
  result: MissionResult;
}

export const IntelligenceReport: React.FC<IntelligenceReportProps> = ({ result }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(result.briefing);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="cyber-panel rounded-xl p-5 border border-emerald-500/40 bg-gradient-to-b from-emerald-950/10 to-[#0a101d] shadow-[0_0_30px_rgba(16,185,129,0.1)]">
      <div className="flex items-center justify-between pb-3 border-b border-emerald-500/20 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold tracking-wide text-slate-100 flex items-center gap-2">
              DECRYPTED INTELLIGENCE BRIEFING
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                VERIFIED
              </span>
            </h3>
            <p className="text-[11px] font-mono text-slate-400">
              Recovered & Authenticated via FYKO Artificial Neural Network AES-256 Key
            </p>
          </div>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>COPIED</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-slate-400" />
              <span>COPY BRIEFING</span>
            </>
          )}
        </button>
      </div>

      {/* Main Intelligence Text */}
      <div className="bg-black/50 p-4 rounded-lg border border-slate-800/80 mb-4 text-slate-200 text-sm leading-relaxed font-sans font-normal relative">
        <div className="text-[10px] font-mono uppercase text-emerald-500/70 mb-2 tracking-wider">
          CLASSIFIED REPORT CONTENT:
        </div>
        <p className="whitespace-pre-line select-text text-slate-100">{result.briefing}</p>
      </div>

      {/* Audit & Cryptographic Verification Metadata */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-xs font-mono">
        <div className="bg-[#0e1626] p-2.5 rounded border border-slate-800/80">
          <div className="flex items-center gap-1 text-[10px] text-slate-400 mb-0.5">
            <Cpu className="w-3 h-3 text-cyan-400" />
            <span>ANN MODEL ULID</span>
          </div>
          <div className="text-cyan-300 font-semibold truncate">{result.modelUlid || '01J4X8KM79NV2B104PLQ9'}</div>
        </div>

        <div className="bg-[#0e1626] p-2.5 rounded border border-slate-800/80">
          <div className="flex items-center gap-1 text-[10px] text-slate-400 mb-0.5">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>DERIVED AES-256 KEY</span>
          </div>
          <div className="text-emerald-400 font-semibold truncate">{result.aesKeyMasked || 'DYNAMIC_VERIFIED'}</div>
        </div>

        <div className="bg-[#0e1626] p-2.5 rounded border border-slate-800/80">
          <div className="flex items-center gap-1 text-[10px] text-slate-400 mb-0.5">
            <Database className="w-3 h-3 text-amber-400" />
            <span>MONGODB AUDIT ULID</span>
          </div>
          <div className="text-amber-300 font-semibold truncate">{result.mongoUlid || '01J4X8KM79NV2B104AUDIT'}</div>
        </div>
      </div>
    </div>
  );
};
