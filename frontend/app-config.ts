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
  companyName: 'HealthifyMe',
  pageTitle: 'HealthifyMe Wellness Companion - Daily Check-In',
  pageDescription: 'Your AI-powered daily wellness check-in companion. Track your mood, energy, and goals with personalized support.',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#00C853', // HealthifyMe-inspired wellness green
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#4CAF50',
  startButtonText: 'Start Wellness Check-In',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
