// Authentication types
export interface LoginRequest {
  license_key: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  session_token: string;
  tier_name: string;
  user_name: string;
  features_enabled: Record<string, boolean>;
}

export interface SessionValidation {
  valid: boolean;
  tier_name?: string;
  features_enabled?: Record<string, boolean>;
  message: string;
}

export interface LicenseTier {
  tier_name: string;
  display_name: string;
  description: string;
  features: string[];
  price: number;
}

// Analysis types
export interface SentimentAnalysis {
  overall_sentiment: string;
  total_articles: number;
  sentiment_scores: {
    average_sentiment: number;
    weighted_avg_from_sources: number;
  };
  sentiment_distribution: {
    positive_percentage: number;
    neutral_percentage: number;
    negative_percentage: number;
  };
  source_breakdown: Record<string, number>;
  recent_articles: Array<{
    source: string;
    text: string;
    sentiment: number;
    timestamp?: string;
  }>;
}

export interface TechnicalAnalysis {
  prediction_summary: {
    prediction: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
  };
  market_analysis: {
    current_price: number;
    price_trend: string;
    volume_trend: string;
    rsi_value: number;
    rsi_condition: string;
  };
}

export interface UnifiedAnalysis {
  summary: {
    data_sources_successful: number;
    total_data_sources: number;
    company_sentiment_status: string;
    industry_sentiment_status: string;
    market_data_status: string;
    technical_analysis_status: string;
  };
  gpt5_prompt?: string;
  analysis_timestamp: string;
}

export interface IndustryAnalysis {
  industry: string;
  industry_sentiment: string;
  peer_analysis: Record<string, {
    company_name: string;
    sentiment: string;
  }>;
}

export interface HistoricalData {
  Date: string;
  Open: number;
  High: number;
  Low: number;
  Close: number;
  Volume: number;
}

// UI types
export interface AnalysisConfig {
  symbol: string;
  analysisType: 'sentiment' | 'technical' | 'unified' | 'industry' | 'historical';
  articles?: number;
  timeframe?: string;
  startDate?: string;
  endDate?: string;
}

export interface LoadingState {
  isLoading: boolean;
  message?: string;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
}