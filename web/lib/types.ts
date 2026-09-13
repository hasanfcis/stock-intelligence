export type ActionCategory =
  | "Strong Buy Setup"
  | "Watch"
  | "Neutral"
  | "Avoid / Sell";

export interface ThesisVsPrice {
  company_quality: string;
  long_term_thesis: string;
  price_state: string;
  action: string;
}

export interface Evidence {
  source_name: string;
  url: string;
  published_at: string;
  summary: string;
}

export interface StockScore {
  ticker: string;
  as_of: string;
  price: number;
  catalyst_score: number;
  technical_score: number;
  sentiment_score: number;
  overall_score: number;
  weights_used: Record<string, number>;
  action_category: ActionCategory;
  why_today: string[];
  thesis_vs_price: ThesisVsPrice;
  entry: [number, number] | null;
  stop: number | null;
  targets: number[];
  risk_reward: number | null;
  confidence: number;
  catalyst_ids: string[];
  sources: Evidence[];
}

export interface MarketContext {
  as_of: string;
  spx_change_pct: number;
  nasdaq_change_pct: number;
  sox_change_pct: number;
  ten_year_yield: number;
  vix: number;
}

export interface ExcludedEntry {
  symbol: string;
  rule_id: string;
  reason: string;
}

export interface DailyReport {
  date: string;
  universe_size: number;
  excluded: ExcludedEntry[];
  market_context: MarketContext;
  scores: StockScore[];
  negative_catalysts: StockScore[];
}

export interface CatalystFeedItem {
  ticker: string;
  source_name: string;
  url: string;
  published_at: string;
  summary: string;
}

export interface HistoryItem {
  ticker: string;
  as_of: string;
  action_category: string;
  overall_score: number;
  forward_5d_return: number | null;
  forward_20d_return: number | null;
}

export interface BucketPerformance {
  bucket: string;
  count: number;
  avg_5d_return: number | null;
  avg_20d_return: number | null;
  win_rate: number | null;
}

export interface HistoryResponse {
  items: HistoryItem[];
  buckets: BucketPerformance[];
  note?: string;
}

export interface Stock {
  symbol: string;
  name: string;
  category: string;
  related_symbols: string[];
}

export interface UniverseResponse {
  universe: Stock[];
  excluded: ExcludedEntry[];
}
