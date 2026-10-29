import React, { useState } from 'react';
import { Play, Square, Sparkles, MessageSquare } from 'lucide-react';

interface MissionControllerProps {
  isRunning: boolean;
  onStart: (prompt: string) => void;
  onCancel: () => void;
}

const PRESET_QUERIES = [
  "What are the top critically acclaimed sci-fi and thriller movies released in the last 12 months?",
  "Tell me about the biggest box-office blockbuster espionage movies recently.",
  "Which recent award-winning cinema releases are must-watch for intelligence operatives?",
];

export const MissionController: React.FC<MissionControllerProps> = ({
  isRunning,
  onStart,
  onCancel,
}) => {
  const [prompt, setPrompt] = useState(
    'What are the most anticipated espionage and action thriller movies released recently?'
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isRunning) return;
    onStart(prompt.trim());
  };

  return (
    <div className="cyber-panel rounded-xl p-5 border border-slate-800">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-mono uppercase tracking-widest text-slate-300 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-cyan-400" />
          Mission Instruction Dispatcher
        </h2>
        <span className="text-[11px] font-mono text-cyan-400 flex items-center gap-1">
          <Sparkles className="w-3.5 h-3.5" />
          A2A Cover Story Protocol
        </span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isRunning}
            rows={3}
            placeholder="Enter movie intelligence inquiry for Secret Plan Creator..."
            className="w-full bg-[#0a0f1d] border border-slate-700/80 rounded-lg p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-sans resize-none transition-all disabled:opacity-50"
          />
        </div>

        {/* Quick Presets */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-slate-500 font-mono text-[11px] mr-1">Presets:</span>
          {PRESET_QUERIES.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              disabled={isRunning}
              onClick={() => setPrompt(preset)}
              className="text-[11px] px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 border border-slate-700/60 transition-colors disabled:opacity-40 truncate max-w-[260px]"
            >
              Preset {idx + 1}: {preset.substring(0, 30)}...
            </button>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-2">
          <div className="text-[11px] font-mono text-slate-500">
            Target: <span className="text-slate-300">Secret Plan Creator (Port 9001)</span>
          </div>

          <div className="flex items-center gap-2">
            {isRunning && (
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 rounded-lg bg-rose-950/60 hover:bg-rose-900 border border-rose-700/60 text-rose-300 text-xs font-mono font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Square className="w-3.5 h-3.5" />
                ABORT MISSION
              </button>
            )}

            <button
              type="submit"
              disabled={isRunning || !prompt.trim()}
              className="px-5 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-mono font-bold flex items-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isRunning ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span>
                  MISSION IN PROGRESS...
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  INITIATE AGENT INTERACTION
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

