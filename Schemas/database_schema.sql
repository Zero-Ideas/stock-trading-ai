-- PostgreSQL Database Schema for Stock Sentiment Analysis
-- Creates tables to store sentiment analysis results with per-symbol organization

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS sentiment_articles CASCADE;
DROP TABLE IF EXISTS sentiment_analyses CASCADE;
DROP TABLE IF EXISTS company_info_cache CASCADE;

-- Function to create per-symbol article tables
CREATE OR REPLACE FUNCTION create_symbol_table(symbol_name VARCHAR(10))
RETURNS VOID AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS articles_%s (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            full_text TEXT NOT NULL,
            raw_extracted_text TEXT,
            extraction_successful BOOLEAN DEFAULT FALSE,
            source VARCHAR(2500) NOT NULL,
            url TEXT UNIQUE NOT NULL,
            url_hash VARCHAR(64) UNIQUE NOT NULL,
            article_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            polarity DECIMAL(8,6) NOT NULL,
            compound DECIMAL(8,6) NOT NULL,
            sentiment_label VARCHAR(20) NOT NULL,
            text_length INTEGER NOT NULL,
            extracted_length INTEGER DEFAULT 0,
            enhancement_ratio DECIMAL(8,1) DEFAULT 0.0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', symbol_name);
    
    -- Create indexes for the new table
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_articles_%s_url_hash ON articles_%s(url_hash)', symbol_name, symbol_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_articles_%s_timestamp ON articles_%s(article_timestamp DESC)', symbol_name, symbol_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_articles_%s_source ON articles_%s(source)', symbol_name, symbol_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_articles_%s_sentiment ON articles_%s(compound DESC)', symbol_name, symbol_name);
END;
$$ LANGUAGE plpgsql;

-- Main sentiment analyses table (for summary/cache purposes)
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

-- Company information cache table
CREATE TABLE company_info_cache (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(500),  -- Full official company name
    common_name VARCHAR(255),   -- Common/short name for searches
    industry VARCHAR(255),      -- Industry classification for industry sentiment analyzer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Individual articles table (legacy - for backward compatibility)
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
    url_hash VARCHAR(64),
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
CREATE INDEX idx_company_info_cache_symbol ON company_info_cache(symbol);
CREATE INDEX idx_company_info_cache_updated_at ON company_info_cache(updated_at DESC);
CREATE INDEX idx_sentiment_articles_analysis_id ON sentiment_articles(analysis_id);
CREATE INDEX idx_sentiment_articles_symbol ON sentiment_articles(symbol);
CREATE INDEX idx_sentiment_articles_source ON sentiment_articles(source);
CREATE INDEX idx_sentiment_articles_timestamp ON sentiment_articles(article_timestamp DESC);
CREATE INDEX idx_sentiment_articles_url_hash ON sentiment_articles(url_hash);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to generate URL hash
CREATE OR REPLACE FUNCTION generate_url_hash(url_text TEXT)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(digest(url_text, 'sha256'), 'hex');
END;
$$ language 'plpgsql';

-- Function to get recent articles from per-symbol table
CREATE OR REPLACE FUNCTION get_recent_articles(symbol_name VARCHAR(10), max_articles INTEGER, max_hours INTEGER DEFAULT 24)
RETURNS TABLE(
    title TEXT,
    full_text TEXT,
    raw_extracted_text TEXT,
    extraction_successful BOOLEAN,
    source VARCHAR(100),
    url TEXT,
    article_timestamp TIMESTAMP WITH TIME ZONE,
    polarity DECIMAL(8,6),
    compound DECIMAL(8,6),
    sentiment_label VARCHAR(20),
    text_length INTEGER,
    extracted_length INTEGER,
    enhancement_ratio DECIMAL(8,1)
) AS $$
BEGIN
    -- Create table if it doesn't exist
    PERFORM create_symbol_table(symbol_name);
    
    -- Return recent articles
    RETURN QUERY EXECUTE format('
        SELECT title, full_text, raw_extracted_text, extraction_successful, source, url,
               article_timestamp, polarity, compound, sentiment_label, text_length,
               extracted_length, enhancement_ratio
        FROM articles_%s
        WHERE article_timestamp > CURRENT_TIMESTAMP - INTERVAL ''%s hours''
        ORDER BY article_timestamp DESC
        LIMIT %s
    ', symbol_name, max_hours, max_articles);
END;
$$ LANGUAGE plpgsql;

-- Function to check if URL exists in per-symbol table
CREATE OR REPLACE FUNCTION url_exists_in_symbol_table(symbol_name VARCHAR(10), url_text TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    url_hash_val VARCHAR(64);
    exists_count INTEGER;
BEGIN
    -- Generate URL hash
    url_hash_val := generate_url_hash(url_text);
    
    -- Create table if it doesn't exist
    PERFORM create_symbol_table(symbol_name);
    
    -- Check if URL hash exists
    EXECUTE format('SELECT COUNT(*) FROM articles_%s WHERE url_hash = $1', symbol_name)
    INTO exists_count
    USING url_hash_val;
    
    RETURN exists_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to insert article into per-symbol table (with duplicate checking)
CREATE OR REPLACE FUNCTION insert_article_to_symbol_table(
    symbol_name VARCHAR(10),
    p_title TEXT,
    p_full_text TEXT,
    p_raw_extracted_text TEXT,
    p_extraction_successful BOOLEAN,
    p_source VARCHAR(100),
    p_url TEXT,
    p_article_timestamp TIMESTAMP WITH TIME ZONE,
    p_polarity DECIMAL(8,6),
    p_compound DECIMAL(8,6),
    p_sentiment_label VARCHAR(20),
    p_text_length INTEGER,
    p_extracted_length INTEGER,
    p_enhancement_ratio DECIMAL(8,1)
) RETURNS INTEGER AS $$
DECLARE
    url_hash_val VARCHAR(64);
    inserted_id INTEGER;
BEGIN
    -- Generate URL hash
    url_hash_val := generate_url_hash(p_url);
    
    -- Create table if it doesn't exist
    PERFORM create_symbol_table(symbol_name);
    
    -- Insert article (will fail if URL hash already exists due to UNIQUE constraint)
    BEGIN
        EXECUTE format('
            INSERT INTO articles_%s (
                title, full_text, raw_extracted_text, extraction_successful,
                source, url, url_hash, article_timestamp, polarity, compound,
                sentiment_label, text_length, extracted_length, enhancement_ratio
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id
        ', symbol_name)
        INTO inserted_id
        USING p_title, p_full_text, p_raw_extracted_text, p_extraction_successful,
              p_source, p_url, url_hash_val, p_article_timestamp, p_polarity,
              p_compound, p_sentiment_label, p_text_length, p_extracted_length,
              p_enhancement_ratio;
        
        RETURN inserted_id;
    EXCEPTION
        WHEN unique_violation THEN
            -- URL already exists, return 0 to indicate duplicate
            RETURN 0;
    END;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER update_sentiment_analyses_updated_at BEFORE UPDATE
    ON sentiment_analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_company_info_cache_updated_at BEFORE UPDATE
    ON company_info_cache FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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

-- Function to get the most recent analysis for a symbol within cache window
CREATE OR REPLACE FUNCTION get_cached_analysis_with_articles(p_symbol VARCHAR(10), p_max_hours DECIMAL DEFAULT 1.0)
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
    neutral_percentage DECIMAL(7,2),
    articles_data JSONB
) AS $$
DECLARE
    cache_cutoff TIMESTAMP WITH TIME ZONE;
    articles_json JSONB;
BEGIN
    cache_cutoff := CURRENT_TIMESTAMP - (p_max_hours || ' hours')::INTERVAL;
    
    -- Get articles from per-symbol table
    EXECUTE format('
        SELECT COALESCE(
            json_agg(
                json_build_object(
                    ''title'', title,
                    ''full_text'', full_text,
                    ''raw_extracted_text'', raw_extracted_text,
                    ''extraction_successful'', extraction_successful,
                    ''source'', source,
                    ''url'', url,
                    ''article_timestamp'', article_timestamp,
                    ''polarity'', polarity,
                    ''compound'', compound,
                    ''sentiment_label'', sentiment_label,
                    ''text_length'', text_length,
                    ''extracted_length'', extracted_length,
                    ''enhancement_ratio'', enhancement_ratio
                )
                ORDER BY article_timestamp DESC
            ),
            ''[]''::json
        )::jsonb
        FROM articles_%s
        WHERE article_timestamp > $1
    ', p_symbol) 
    INTO articles_json
    USING cache_cutoff;
    
    -- Return cached analysis with articles if recent enough
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
        sa.neutral_percentage,
        articles_json
    FROM sentiment_analyses sa
    WHERE sa.symbol = p_symbol 
    AND sa.analysis_timestamp > cache_cutoff
    ORDER BY sa.analysis_timestamp DESC
    LIMIT 1;
    
EXCEPTION
    WHEN undefined_table THEN
        -- Symbol table doesn't exist yet, just return cached analysis without articles
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
            sa.neutral_percentage,
            '[]'::jsonb as articles_data
        FROM sentiment_analyses sa
        WHERE sa.symbol = p_symbol 
        AND sa.analysis_timestamp > cache_cutoff
        ORDER BY sa.analysis_timestamp DESC
        LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Sample query to test functionality
-- SELECT * FROM get_cached_analysis_with_articles('AAPL');
-- SELECT * FROM get_recent_articles('AAPL', 50, 24);