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
  companyName: 'Voice Game Master',
  pageTitle: 'D&D-Style Voice Adventure',
  pageDescription:
    'Experience an interactive fantasy adventure guided by your AI Game Master. Speak your actions and watch the story unfold.',

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
