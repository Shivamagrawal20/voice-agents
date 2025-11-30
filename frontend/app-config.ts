export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  // for LiveKit Cloud Sandbox
  sandboxId?: string;
  agentName?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'AI Voice Agent Challenge',
  pageTitle: 'Day 9: E-commerce Agent',
  pageDescription:
    'Experience an interactive e-commerce voice agent powered by the fastest TTS API - Murf Falcon. Speak naturally and shop with AI assistance.',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#FFB700',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#FFA500',
  startButtonText: 'Begin Adventure',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
