export type StepStatus = 'pending' | 'active' | 'completed' | 'error';

export interface MissionStep {
  id: number;
  label: string;
  source: 'User' | 'Creator' | 'FykoServer' | 'ANN_Worker' | 'Reviewer';
  target: 'Creator' | 'FykoServer' | 'ANN_Worker' | 'Reviewer' | 'User';
  protocol: 'HTTP' | 'AMQP' | 'GridFS' | 'RSA-OAEP' | 'A2A / AES-256' | 'Local';
  description: string;
  timestamp?: string;
  status: StepStatus;
  payloadSnippet?: string;
}

export interface ServiceHealth {
  fykoServer: 'online' | 'offline' | 'checking';
  secretPlanCreator: 'online' | 'offline' | 'checking';
  secretPlanReviewer: 'online' | 'offline' | 'checking';
  workerPool: 'online' | 'offline' | 'checking';
  rabbitMq: 'online' | 'offline' | 'checking';
}

export interface MissionResult {
  query: string;
  modelUlid?: string;
  randomString?: string;
  utcTime?: number;
  aesKeyMasked?: string;
  encryptedQuery?: string;
  encryptedResponse?: string;
  rawPlaintext?: string;
  briefing: string;
  mongoUlid?: string;
}

