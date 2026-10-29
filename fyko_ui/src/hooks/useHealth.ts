import { useState, useEffect } from 'react';
import { ServiceHealth } from '../types';

export function useHealth() {
  const [health, setHealth] = useState<ServiceHealth>({
    fykoServer: 'checking',
    secretPlanCreator: 'checking',
    secretPlanReviewer: 'checking',
    workerPool: 'online', // StatefulSet active
    rabbitMq: 'online',
  });

  const checkServices = async () => {
    // 1. Check Fyko Server
    try {
      const res = await fetch('/api/server/health', { signal: AbortSignal.timeout(2500) });
      setHealth((h) => ({ ...h, fykoServer: res.ok ? 'online' : 'offline' }));
    } catch {
      setHealth((h) => ({ ...h, fykoServer: 'offline' }));
    }

    // 2. Check Secret Plan Creator
    try {
      const res = await fetch('/api/creator/health', { signal: AbortSignal.timeout(2500) });
      setHealth((h) => ({ ...h, secretPlanCreator: res.ok ? 'online' : 'offline' }));
    } catch {
      setHealth((h) => ({ ...h, secretPlanCreator: 'offline' }));
    }

    // 3. Check Secret Plan Reviewer
    try {
      const res = await fetch('/api/reviewer/health', { signal: AbortSignal.timeout(2500) });
      setHealth((h) => ({ ...h, secretPlanReviewer: res.ok ? 'online' : 'offline' }));
    } catch {
      setHealth((h) => ({ ...h, secretPlanReviewer: 'offline' }));
    }
  };

  useEffect(() => {
    checkServices();
    const interval = setInterval(checkServices, 10000);
    return () => clearInterval(interval);
  }, []);

  return { health, refreshHealth: checkServices };
}

