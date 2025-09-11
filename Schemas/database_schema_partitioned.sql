-- PostgreSQL Database Schema for Stock Sentiment Analysis (Partitioned Version)
-- Migrates from per-symbol tables to single partitioned table for better performance and management

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drop old tables and functions if they exist
DROP FUNCTION IF EXISTS create_symbol_table(VARCHAR(10)) CASCADE;
DROP FUNCTION IF EXISTS get_recent_articles(VARCHAR(10), INTEGER, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS url_exists_in_symbol_table(VARCHAR(10), TEXT) CASCADE;
DROP FUNCTION IF EXISTS insert_article_to_symbol_table(VARCHAR(10), TEXT, TEXT, TEXT, BOOLEAN, VARCHAR(100), TEXT, TIMESTAMP WITH TIME ZONE, DECIMAL(8,6), DECIMAL(8,6), VARCHAR(20), INTEGER, INTEGER, DECIMAL(8,1)) CASCADE;
DROP FUNCTION IF EXISTS get_cached_analysis_with_articles(VARCHAR(10), DECIMAL) CASCADE;

-- Keep existing sentiment_analyses table (no changes needed)
-- CREATE TABLE sentiment_analyses is already defined and working

-- Create the main partitioned articles table
DROP TABLE IF EXISTS articles_partitioned CASCADE;
CREATE TABLE articles_partitioned (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    full_text TEXT NOT NULL,
    raw_extracted_text TEXT,
    extraction_successful BOOLEAN DEFAULT FALSE,
    source VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    url_hash VARCHAR(64) NOT NULL,
    article_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    polarity DECIMAL(8,6) NOT NULL,
    compound DECIMAL(8,6) NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    text_length INTEGER NOT NULL,
    extracted_length INTEGER DEFAULT 0,
    enhancement_ratio DECIMAL(8,1) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT articles_partitioned_url_symbol_unique UNIQUE (url_hash, symbol),
    CONSTRAINT articles_partitioned_sentiment_check CHECK (compound >= -1.0 AND compound <= 1.0),
    CONSTRAINT articles_partitioned_polarity_check CHECK (polarity >= -1.0 AND polarity <= 1.0)
) PARTITION BY HASH (symbol);

-- Create partitions for common stock symbols (you can add more as needed)
-- We'll create 16 partitions to distribute the load
CREATE TABLE articles_partitioned_p0 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 0);
CREATE TABLE articles_partitioned_p1 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 1);
CREATE TABLE articles_partitioned_p2 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 2);
CREATE TABLE articles_partitioned_p3 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 3);
CREATE TABLE articles_partitioned_p4 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 4);
CREATE TABLE articles_partitioned_p5 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 5);
CREATE TABLE articles_partitioned_p6 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 6);
CREATE TABLE articles_partitioned_p7 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 7);
CREATE TABLE articles_partitioned_p8 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 8);
CREATE TABLE articles_partitioned_p9 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 9);
CREATE TABLE articles_partitioned_p10 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 10);
CREATE TABLE articles_partitioned_p11 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 11);
CREATE TABLE articles_partitioned_p12 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 12);
CREATE TABLE articles_partitioned_p13 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 13);
CREATE TABLE articles_partitioned_p14 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 14);
CREATE TABLE articles_partitioned_p15 PARTITION OF articles_partitioned FOR VALUES WITH (modulus 16, remainder 15);

-- Create indexes on the main partitioned table (will automatically apply to all partitions)
CREATE INDEX idx_articles_partitioned_symbol ON articles_partitioned(symbol);
CREATE INDEX idx_articles_partitioned_timestamp ON articles_partitioned(article_timestamp DESC);
CREATE INDEX idx_articles_partitioned_symbol_timestamp ON articles_partitioned(symbol, article_timestamp DESC);
CREATE INDEX idx_articles_partitioned_source ON articles_partitioned(source);
CREATE INDEX idx_articles_partitioned_sentiment ON articles_partitioned(compound DESC);
CREATE INDEX idx_articles_partitioned_url_hash ON articles_partitioned(url_hash);

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

-- Function to get recent articles from partitioned table
CREATE OR REPLACE FUNCTION get_recent_articles_partitioned(symbol_name VARCHAR(10), max_articles INTEGER, max_hours INTEGER DEFAULT 24)
RETURNS TABLE(
    title TEXT,
    full_text TEXT,
    raw_extracted_text TEXT,
    extraction_successful BOOLEAN,
    source VARCHAR(255),
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
    RETURN QUERY 
    SELECT 
        a.title,
        a.full_text,
        a.raw_extracted_text,
        a.extraction_successful,
        a.source,
        a.url,
        a.article_timestamp,
        a.polarity,
        a.compound,
        a.sentiment_label,
        a.text_length,
        a.extracted_length,
        a.enhancement_ratio
    FROM articles_partitioned a
    WHERE a.symbol = symbol_name
    AND a.article_timestamp > CURRENT_TIMESTAMP - (max_hours || ' hours')::INTERVAL
    ORDER BY a.article_timestamp DESC
    LIMIT max_articles;
END;
$$ LANGUAGE plpgsql;

-- Function to check if URL exists in partitioned table
CREATE OR REPLACE FUNCTION url_exists_partitioned(symbol_name VARCHAR(10), url_text TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    url_hash_val VARCHAR(64);
    exists_count INTEGER;
BEGIN
    -- Generate URL hash
    url_hash_val := generate_url_hash(url_text);
    
    -- Check if URL hash exists for this symbol
    SELECT COUNT(*) INTO exists_count
    FROM articles_partitioned 
    WHERE symbol = symbol_name AND url_hash = url_hash_val;
    
    RETURN exists_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to insert article into partitioned table (with duplicate checking)
CREATE OR REPLACE FUNCTION insert_article_partitioned(
    symbol_name VARCHAR(10),
    p_title TEXT,
    p_full_text TEXT,
    p_raw_extracted_text TEXT,
    p_extraction_successful BOOLEAN,
    p_source VARCHAR(255),
    p_url TEXT,
    p_article_timestamp TIMESTAMP WITH TIME ZONE,
    p_polarity DECIMAL(8,6),
    p_compound DECIMAL(8,6),
    p_sentiment_label VARCHAR(20),
    p_text_length INTEGER,
    p_extracted_length INTEGER,
    p_enhancement_ratio DECIMAL(8,1)
) RETURNS BIGINT AS $$
DECLARE
    url_hash_val VARCHAR(64);
    inserted_id BIGINT;
BEGIN
    -- Generate URL hash
    url_hash_val := generate_url_hash(p_url);
    
    -- Insert article (will fail if URL hash + symbol combination already exists due to UNIQUE constraint)
    BEGIN
        INSERT INTO articles_partitioned (
            symbol, title, full_text, raw_extracted_text, extraction_successful,
            source, url, url_hash, article_timestamp, polarity, compound,
            sentiment_label, text_length, extracted_length, enhancement_ratio
        ) VALUES (
            symbol_name, p_title, p_full_text, p_raw_extracted_text, p_extraction_successful,
            p_source, p_url, url_hash_val, p_article_timestamp, p_polarity, p_compound,
            p_sentiment_label, p_text_length, p_extracted_length, p_enhancement_ratio
        ) RETURNING id INTO inserted_id;
        
        RETURN inserted_id;
    EXCEPTION
        WHEN unique_violation THEN
            -- URL already exists for this symbol, return 0 to indicate duplicate
            RETURN 0;
    END;
END;
$$ LANGUAGE plpgsql;

-- Function to get cached analysis with articles from partitioned table
CREATE OR REPLACE FUNCTION get_cached_analysis_with_articles_partitioned(p_symbol VARCHAR(10), p_max_hours DECIMAL DEFAULT 1.0)
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
    
    -- Get articles from partitioned table
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'title', a.title,
                'full_text', a.full_text,
                'raw_extracted_text', a.raw_extracted_text,
                'extraction_successful', a.extraction_successful,
                'source', a.source,
                'url', a.url,
                'article_timestamp', a.article_timestamp,
                'polarity', a.polarity,
                'compound', a.compound,
                'sentiment_label', a.sentiment_label,
                'text_length', a.text_length,
                'extracted_length', a.extracted_length,
                'enhancement_ratio', a.enhancement_ratio
            )
            ORDER BY a.article_timestamp DESC
        ),
        '[]'::jsonb
    ) INTO articles_json
    FROM articles_partitioned a
    WHERE a.symbol = p_symbol 
    AND a.article_timestamp > cache_cutoff;
    
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
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at
CREATE TRIGGER update_articles_partitioned_updated_at 
    BEFORE UPDATE ON articles_partitioned 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add trigger to existing sentiment_analyses table if not exists
DROP TRIGGER IF EXISTS update_sentiment_analyses_updated_at ON sentiment_analyses;
CREATE TRIGGER update_sentiment_analyses_updated_at BEFORE UPDATE
    ON sentiment_analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for recent analyses per symbol (unchanged)
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

-- Utility functions for migration
CREATE OR REPLACE FUNCTION list_symbol_tables()
RETURNS TABLE(table_name TEXT, symbol VARCHAR(10)) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.table_name::TEXT,
        replace(t.table_name, 'articles_', '')::VARCHAR(10) as symbol
    FROM information_schema.tables t
    WHERE t.table_schema = 'public' 
    AND t.table_name LIKE 'articles_%'
    AND t.table_name != 'articles_partitioned'
    ORDER BY t.table_name;
END;
$$ LANGUAGE plpgsql;

-- Function to get count of articles in partitioned table by symbol
CREATE OR REPLACE FUNCTION get_partitioned_article_count(p_symbol VARCHAR(10))
RETURNS INTEGER AS $$
DECLARE
    article_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO article_count
    FROM articles_partitioned
    WHERE symbol = p_symbol;
    
    RETURN article_count;
END;
$$ LANGUAGE plpgsql;

-- Sample queries to test functionality
-- SELECT * FROM get_cached_analysis_with_articles_partitioned('AAPL');
-- SELECT * FROM get_recent_articles_partitioned('AAPL', 50, 24);
-- SELECT * FROM list_symbol_tables();