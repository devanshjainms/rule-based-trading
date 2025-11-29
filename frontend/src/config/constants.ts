// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// App Configuration
export const APP_NAME = 'TradePilot';
export const APP_VERSION = '2.0.0';

// Polling intervals (in milliseconds)
export const POSITIONS_POLL_INTERVAL = 1000;
export const ENGINE_STATUS_POLL_INTERVAL = 2000;
export const RULES_POLL_INTERVAL = 5000;

// Storage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  THEME: 'theme',
  USER: 'user',
} as const;

// Route paths
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  POSITIONS: '/positions',
  RULES: '/rules',
  RULES_CREATE: '/rules/create',
  RULES_EDIT: '/rules/:id',
  TRADES: '/trades',
  SETTINGS: '/settings',
  BROKER_CONNECT: '/broker/connect',
} as const;

// Broker types
export const BROKERS = {
  KITE: 'kite',
} as const;

// Position types
export const POSITION_TYPES = {
  LONG: 'LONG',
  SHORT: 'SHORT',
  ALL: 'ALL',
} as const;

// Order types
export const ORDER_TYPES = {
  MARKET: 'market',
  LIMIT: 'limit',
} as const;

// Condition types
export const CONDITION_TYPES = {
  RELATIVE: 'relative',
  ABSOLUTE: 'absolute',
} as const;
