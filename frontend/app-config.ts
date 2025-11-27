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
  companyName: 'Falcon National Bank',
  pageTitle: 'Falcon National Fraud Alert Desk',
  pageDescription:
    'Connect with Falcon National’s automated fraud specialist to review suspicious transactions in a safe sandbox demo.',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#0047AB',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#012A5B',
  startButtonText: 'Start Fraud Review',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
