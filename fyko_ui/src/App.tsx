import React from 'react';
import { Header } from './components/Header';
import { AgentCard } from './components/AgentCard';
import { NetworkFlowVisualizer } from './components/NetworkFlowVisualizer';
import { MissionController } from './components/MissionController';
import { TelemetryLog } from './components/TelemetryLog';
import { IntelligenceReport } from './components/IntelligenceReport';
import { AnnPipelineStatus } from './components/AnnPipelineStatus';
import { useHealth } from './hooks/useHealth';
import { useMission } from './hooks/useMission';

export const App: React.FC = () => {
  const { health, refreshHealth } = useHealth();
  const {
    isRunning,
    steps,
    activeStepId,
    result,
    logs,
    simulatedAnnProgress,
    startMission,
    cancelMission,
  } = useMission();

  // Find active step snippet
  const activeStep = steps.find((s) => s.id === activeStepId);

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col font-sans">
      <Header health={health} refreshHealth={refreshHealth} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 lg:p-8 space-y-6">
        {/* Top Section: Agent Profiles */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <AgentCard
            type="creator"
            isActive={isRunning && activeStepId !== null && [1, 2, 4, 5, 6, 7, 8, 10, 11].includes(activeStepId)}
            activeAction={activeStep?.source === 'Creator' ? activeStep?.label : undefined}
            keysInfo={{
              annModelUlid: steps[1]?.payloadSnippet?.replace('ULID: ', '') || '01J4X8KM79NV2B104PLQ9',
              aesKeyStatus: steps[4]?.status === 'completed' ? 'DYNAMIC 256-BIT KEY LOADED' : undefined,
            }}
          />

          <AgentCard
            type="reviewer"
            isActive={isRunning && activeStepId !== null && [7, 8, 9, 10].includes(activeStepId)}
            activeAction={activeStep?.target === 'Reviewer' || activeStep?.source === 'Reviewer' ? activeStep?.label : undefined}
            keysInfo={{
              annModelUlid: steps[1]?.payloadSnippet?.replace('ULID: ', '') || '01J4X8KM79NV2B104PLQ9',
              aesKeyStatus: steps[6]?.status === 'completed' ? 'SYNCHRONIZED (RSA-OAEP)' : undefined,
            }}
          />
        </section>

        {/* Mission Input Form */}
        <section>
          <MissionController
            isRunning={isRunning}
            onStart={startMission}
            onCancel={cancelMission}
          />
        </section>

        {/* Network & Cryptographic Transmission Flow Visualizer */}
        <section>
          <NetworkFlowVisualizer
            activeStepId={activeStepId}
            steps={steps}
            annProgress={simulatedAnnProgress}
          />
        </section>

        {/* Final Report (Appears when completed) */}
        {result && (
          <section className="animate-fade-in">
            <IntelligenceReport result={result} />
          </section>
        )}

        {/* Bottom Split: Stepper & Telemetry Log */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AnnPipelineStatus steps={steps} activeStepId={activeStepId} />
          <TelemetryLog logs={logs} />
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-[#060910] py-4 text-center text-xs font-mono text-slate-500">
        FYKO_SERVER & SECURE_AGENTS ARCHITECTURE • SECRET PLAN EXCHANGE & EVALUATION • MITRA J.S. THESIS IMPLEMENTATION
      </footer>
    </div>
  );
};

export default App;

