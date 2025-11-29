// User types
export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

// Rule types
export interface RuleCondition {
  indicator: string;
  operator: string;
  value: number | string;
  timeframe?: string;
}

export interface RuleAction {
  action: string;
  quantity?: number;
  quantity_percent?: number;
  order_type: string;
  price?: number;
}

export interface TakeProfitCondition {
  enabled: boolean;
  condition_type: 'relative' | 'absolute';
  target: number;
  trail?: boolean;
  trail_step?: number;
}

export interface StopLossCondition {
  enabled: boolean;
  condition_type: 'relative' | 'absolute';
  stop: number;
  trail?: boolean;
  trail_step?: number;
}

export interface TimeCondition {
  start_time?: string;
  end_time?: string;
  square_off_time?: string;
  active_days?: number[];
}

export interface Rule {
  id: string;
  name: string;
  description?: string;
  symbol: string;
  conditions: RuleCondition[];
  actions: RuleAction[];
  is_active: boolean;
  priority: number;
  trigger_count: number;
  last_triggered?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateRuleRequest {
  name: string;
  description?: string;
  symbol: string;
  conditions: RuleCondition[];
  actions: RuleAction[];
  is_active?: boolean;
  priority?: number;
}

export interface UpdateRuleRequest {
  name?: string;
  description?: string;
  symbol?: string;
  conditions?: RuleCondition[];
  actions?: RuleAction[];
  is_active?: boolean;
  priority?: number;
}

// Position types
export interface Position {
  symbol: string;
  exchange: string;
  quantity: number;
  average_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
  position_type: 'LONG' | 'SHORT';
  product: 'CNC' | 'MIS' | 'NRML';
  day_quantity?: number;
  overnight_quantity?: number;
}

// Trade types
export interface Trade {
  id: string;
  symbol: string;
  exchange: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  order_id?: string;
  order_type: string;
  trigger_type?: string;
  trigger_price?: number;
  pnl?: number;
  status: string;
  executed_at: string;
}

// Order types
export interface Order {
  order_id: string;
  symbol: string;
  exchange: string;
  transaction_type: 'BUY' | 'SELL';
  quantity: number;
  price?: number;
  order_type: string;
  status: string;
  filled_quantity: number;
  pending_quantity: number;
  average_price?: number;
  placed_at: string;
}

// Broker types
export interface BrokerAccount {
  id: string;
  broker_type: string;
  api_key_masked: string;
  is_active: boolean;
  is_connected: boolean;
  token_expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface BrokerStatus {
  connected: boolean;
  broker_type: string;
  message: string;
  action?: string;
}

export interface BrokerOAuthResponse {
  auth_url: string;
  state: string;
  message: string;
}

// Engine types
export interface EngineStatus {
  running: boolean;
  user_id: string;
  active_trades: number;
  rules_loaded: number;
  started_at?: string;
  message?: string;
}

// API Response types
export interface ApiError {
  detail: string | { message: string; error: string };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
