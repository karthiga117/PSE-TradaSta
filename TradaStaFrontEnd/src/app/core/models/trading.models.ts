export interface MarketPriceResponse {
  symbol: string;
  price: string;
  currency: string;
  timestamp: string | Date;
}

export interface MarketCandleResponse {
  symbol: string;
  timestamp: string | Date;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface OhlcvResponse {
  symbol: string;
  timeframe: string;
  candles: MarketCandleResponse[];
}

export interface TechnicalAnalysisIndicatorSummary {
  sma?: { period: number; value: string } | null;
  ema?: { period: number; value: string } | null;
  rsi?: { period: number; value: string } | null;
  macd?: {
    fast_period: number;
    slow_period: number;
    signal_period: number;
    macd: string;
    signal: string;
    histogram: string;
  } | null;
  bollinger_bands?: {
    period: number;
    stddev: string;
    upper: string;
    middle: string;
    lower: string;
  } | null;
  atr?: { period: number; value: string } | null;
  volume?: {
    period: number;
    current_volume: string;
    average_volume: string;
    volume_ratio: string;
  } | null;
}

export interface TechnicalAnalysisStrategy {
  strategy_name: string;
  direction: string;
  rationale: string;
  indicator_values: Record<string, string | number>;
}

export interface TechnicalAnalysisResponse {
  symbol: string;
  timeframe: string;
  timestamp: string;
  trend: string;
  indicators: TechnicalAnalysisIndicatorSummary;
  strategies: TechnicalAnalysisStrategy[];
}

export interface RiskEvaluationRequest {
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry_price: number | string;
  stop_loss?: number | string | null;
  take_profit?: number | string | null;
  account_equity?: number | string | null;
  current_exposure?: number | string | null;
  daily_loss?: number | string | null;
  peak_equity?: number | string | null;
  current_equity?: number | string | null;
  open_positions?: number | null;
}

export interface RiskDecisionResponse {
  approved: boolean;
  reason_code: string;
  reason: string;
  risk_amount: string | null;
  position_size: string | null;
  risk_reward_ratio: string | null;
  portfolio_exposure: string | null;
  warnings: string[];
}

export interface SignalRequestPayload {
  symbol: string;
  timeframe?: string;
  strategy?: string | null;
  account_equity?: number | string | null;
  current_exposure?: number | string | null;
  daily_loss?: number | string | null;
  peak_equity?: number | string | null;
  current_equity?: number | string | null;
  open_positions?: number | null;
  strategy_parameters?: Record<string, unknown>;
  risk_configuration_overrides?: Record<string, unknown>;
}

export interface SignalResponse {
  signal: string;
  symbol: string;
  price: string | null;
  indicators: Record<string, string>;
  strategy: string;
  confidence: string;
  entry: string | null;
  stop_loss: string | null;
  take_profit: string | null;
  risk_reward: string | null;
  risk_reward_ratio: string | null;
  reasoning: string;
  timestamp: string;
}

export interface KnowledgeSearchResult {
  chunk_id: string;
  content: string;
  score: number;
  document_id: string;
  title: string;
  source: string;
  section?: string | null;
  metadata: Record<string, unknown>;
}

export interface KnowledgeSearchResponse {
  query: string;
  results: KnowledgeSearchResult[];
}

export interface KnowledgeContextResponse {
  query: string;
  sources: string[];
  chunks: string[];
  total_results: number;
  context_text: string;
}

export interface AiExplanationResponse {
  signal: string;
  confidence: string;
  explanation: string;
  keyFactors: string[];
  risks: string[];
  entry: string | null;
  stopLoss: string | null;
  takeProfit: string | null;
  riskReward: string | null;
  riskRewardRatio: string | null;
  knowledgeSources: string[];
}

export interface DashboardState {
  price: MarketPriceResponse | null;
  ohlcv: OhlcvResponse | null;
  analysis: TechnicalAnalysisResponse | null;
  signal: SignalResponse | null;
  risk: RiskDecisionResponse | null;
  explanation: AiExplanationResponse | null;
  knowledge: KnowledgeSearchResponse | null;
}
