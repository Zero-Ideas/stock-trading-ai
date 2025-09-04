-- PostgreSQL Database Schema for Stock Sentiment Analysis
-- Creates tables to store sentiment analysis results with caching functionality

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS sentiment_articles CASCADE;
DROP TABLE IF EXISTS sentiment_analyses CASCADE;

-- Main sentiment analyses table
CREATE TABLE sentiment_analyses (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    target_articles INTEGER DEFAULT 50,
    total_articles INTEGER NOT NULL,
    overall_sentiment VARCHAR(20) NOT NULL,
    average_sentiment DECIMAL(8,6) NOT NULL,
    weighted_avg_from_sources DECIMAL(8,6) NOT NULL,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    positive_percentage DECIMAL(7,2) DEFAULT 0.0,
    negative_percentage DECIMAL(7,2) DEFAULT 0.0,
    neutral_percentage DECIMAL(7,2) DEFAULT 0.0,
    source_breakdown JSONB,
    newspaper3k_stats JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Individual articles table
CREATE TABLE sentiment_articles (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES sentiment_analyses(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    full_text TEXT NOT NULL,
    raw_extracted_text TEXT,
    extraction_successful BOOLEAN DEFAULT FALSE,
    source VARCHAR(100) NOT NULL,
    url TEXT,
    article_timestamp TIMESTAMP WITH TIME ZONE,
    polarity DECIMAL(8,6) NOT NULL,
    compound DECIMAL(8,6) NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    text_length INTEGER NOT NULL,
    extracted_length INTEGER DEFAULT 0,
    enhancement_ratio DECIMAL(8,1) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_sentiment_analyses_symbol ON sentiment_analyses(symbol);
CREATE INDEX idx_sentiment_analyses_timestamp ON sentiment_analyses(analysis_timestamp DESC);
CREATE INDEX idx_sentiment_analyses_symbol_timestamp ON sentiment_analyses(symbol, analysis_timestamp DESC);
CREATE INDEX idx_sentiment_articles_analysis_id ON sentiment_articles(analysis_id);
CREATE INDEX idx_sentiment_articles_symbol ON sentiment_articles(symbol);
CREATE INDEX idx_sentiment_articles_source ON sentiment_articles(source);
CREATE INDEX idx_sentiment_articles_timestamp ON sentiment_articles(article_timestamp DESC);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_sentiment_analyses_updated_at BEFORE UPDATE
    ON sentiment_analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for recent analyses per symbol
CREATE OR REPLACE VIEW recent_analyses AS
SELECT DISTINCT ON (symbol) 
    id,
    symbol,
    company_name,
    analysis_timestamp,
    total_articles,
    overall_sentiment,
    average_sentiment,
    weighted_avg_from_sources,
    positive_percentage,
    negative_percentage,
    neutral_percentage
FROM sentiment_analyses 
ORDER BY symbol, analysis_timestamp DESC;

-- View for cache checking (analyses within last hour)
CREATE OR REPLACE VIEW cached_analyses AS
SELECT 
    id,
    symbol,
    company_name,
    analysis_timestamp,
    total_articles,
    overall_sentiment,
    average_sentiment,
    weighted_avg_from_sources,
    source_breakdown,
    positive_count,
    negative_count,
    neutral_count,
    positive_percentage,
    negative_percentage,
    neutral_percentage
FROM sentiment_analyses 
WHERE analysis_timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
ORDER BY symbol, analysis_timestamp DESC;

-- Function to get the most recent analysis for a symbol within cache window
CREATE OR REPLACE FUNCTION get_cached_analysis(p_symbol VARCHAR(10))
RETURNS TABLE(
    analysis_id INTEGER,
    symbol VARCHAR(10),
    company_name VARCHAR(255),
    analysis_timestamp TIMESTAMP WITH TIME ZONE,
    total_articles INTEGER,
    overall_sentiment VARCHAR(20),
    average_sentiment DECIMAL(8,6),
    weighted_avg_from_sources DECIMAL(8,6),
    source_breakdown JSONB,
    positive_count INTEGER,
    negative_count INTEGER,
    neutral_count INTEGER,
    positive_percentage DECIMAL(7,2),
    negative_percentage DECIMAL(7,2),
    neutral_percentage DECIMAL(7,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sa.id,
        sa.symbol,
        sa.company_name,
        sa.analysis_timestamp,
        sa.total_articles,
        sa.overall_sentiment,
        sa.average_sentiment,
        sa.weighted_avg_from_sources,
        sa.source_breakdown,
        sa.positive_count,
        sa.negative_count,
        sa.neutral_count,
        sa.positive_percentage,
        sa.negative_percentage,
        sa.neutral_percentage
    FROM sentiment_analyses sa
    WHERE sa.symbol = p_symbol 
    AND sa.analysis_timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
    ORDER BY sa.analysis_timestamp DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Sample query to test cache functionality
-- SELECT * FROM get_cached_analysis('AAPL');