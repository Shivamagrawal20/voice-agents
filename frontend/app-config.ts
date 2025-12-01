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
  pageTitle: 'Day 10: Improv Battle',
  pageDescription:
    'Step onto the Improv Battle stage with a high-energy voice host powered by the fastest TTS API - Murf Falcon. Play through short-form improv scenes and get live reactions to your performance.',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#FFB700',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#FFA500',
  startButtonText: 'Start Improv Battle',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
