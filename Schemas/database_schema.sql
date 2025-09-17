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

-- License key management tables
CREATE TABLE license_tiers (
    id SERIAL PRIMARY KEY,
    tier_name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    max_concurrent_sessions INTEGER DEFAULT 1,
    max_api_calls_per_hour INTEGER DEFAULT 100,
    max_api_calls_per_day INTEGER DEFAULT 1000,
    features_enabled JSONB DEFAULT '{}',
    price_monthly DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE license_keys (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(64) UNIQUE NOT NULL,
    tier_id INTEGER REFERENCES license_tiers(id) ON DELETE RESTRICT,
    user_name VARCHAR(255),
    user_email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    disabled_message TEXT,
    usage_stats JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE license_sessions (
    id SERIAL PRIMARY KEY,
    license_key_id INTEGER REFERENCES license_keys(id) ON DELETE CASCADE,
    session_token VARCHAR(64) UNIQUE NOT NULL,
    device_fingerprint VARCHAR(255),
    user_agent TEXT,
    ip_address INET,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_usage_logs (
    id SERIAL PRIMARY KEY,
    license_key_id INTEGER REFERENCES license_keys(id) ON DELETE CASCADE,
    session_id INTEGER REFERENCES license_sessions(id) ON DELETE SET NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_size INTEGER DEFAULT 0,
    response_size INTEGER DEFAULT 0,
    response_status INTEGER,
    processing_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for license management
CREATE INDEX idx_license_keys_key ON license_keys(license_key);
CREATE INDEX idx_license_keys_tier ON license_keys(tier_id);
CREATE INDEX idx_license_keys_active ON license_keys(is_active);
CREATE INDEX idx_license_keys_expires ON license_keys(expires_at);
CREATE INDEX idx_license_sessions_key_id ON license_sessions(license_key_id);
CREATE INDEX idx_license_sessions_token ON license_sessions(session_token);
CREATE INDEX idx_license_sessions_active ON license_sessions(is_active);
CREATE INDEX idx_license_sessions_expires ON license_sessions(expires_at);
CREATE INDEX idx_api_usage_logs_key_id ON api_usage_logs(license_key_id);
CREATE INDEX idx_api_usage_logs_timestamp ON api_usage_logs(request_timestamp);

-- Triggers for license management
CREATE TRIGGER update_license_tiers_updated_at BEFORE UPDATE
    ON license_tiers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_license_keys_updated_at BEFORE UPDATE
    ON license_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate secure license keys
CREATE OR REPLACE FUNCTION generate_license_key()
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(gen_random_bytes(32), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Function to generate session tokens
CREATE OR REPLACE FUNCTION generate_session_token()
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(gen_random_bytes(32), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Function to validate license key and check permissions
CREATE OR REPLACE FUNCTION validate_license_key(p_license_key VARCHAR(64))
RETURNS TABLE(
    valid BOOLEAN,
    license_id INTEGER,
    tier_name VARCHAR(50),
    user_name VARCHAR(255),
    features_enabled JSONB,
    max_concurrent_sessions INTEGER,
    current_sessions INTEGER,
    message TEXT
) AS $$
DECLARE
    key_record RECORD;
    session_count INTEGER;
BEGIN
    -- Get license key details
    SELECT lk.id, lk.is_active, lk.expires_at, lk.disabled_message, lk.user_name,
           lt.tier_name, lt.features_enabled, lt.max_concurrent_sessions
    INTO key_record
    FROM license_keys lk
    JOIN license_tiers lt ON lk.tier_id = lt.id
    WHERE lk.license_key = p_license_key;

    -- Check if key exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::VARCHAR(50), NULL::VARCHAR(255),
                           NULL::JSONB, NULL::INTEGER, NULL::INTEGER, 'Invalid license key'::TEXT;
        RETURN;
    END IF;

    -- Check if key is active
    IF NOT key_record.is_active THEN
        RETURN QUERY SELECT FALSE, key_record.id, key_record.tier_name, key_record.user_name,
                           key_record.features_enabled, key_record.max_concurrent_sessions, NULL::INTEGER,
                           COALESCE(key_record.disabled_message, 'License key is disabled')::TEXT;
        RETURN;
    END IF;

    -- Check if key has expired
    IF key_record.expires_at IS NOT NULL AND key_record.expires_at < CURRENT_TIMESTAMP THEN
        RETURN QUERY SELECT FALSE, key_record.id, key_record.tier_name, key_record.user_name,
                           key_record.features_enabled, key_record.max_concurrent_sessions, NULL::INTEGER,
                           'License key has expired'::TEXT;
        RETURN;
    END IF;

    -- Count active sessions
    SELECT COUNT(*)
    INTO session_count
    FROM license_sessions ls
    WHERE ls.license_key_id = key_record.id
    AND ls.is_active = TRUE
    AND (ls.expires_at IS NULL OR ls.expires_at > CURRENT_TIMESTAMP);

    -- Return validation result
    RETURN QUERY SELECT TRUE, key_record.id, key_record.tier_name, key_record.user_name,
                       key_record.features_enabled, key_record.max_concurrent_sessions, session_count,
                       'License key is valid'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to create a new session
CREATE OR REPLACE FUNCTION create_license_session(
    p_license_key VARCHAR(64),
    p_device_fingerprint VARCHAR(255),
    p_user_agent TEXT,
    p_ip_address INET,
    p_session_duration_hours INTEGER DEFAULT 24
)
RETURNS TABLE(
    success BOOLEAN,
    session_token VARCHAR(64),
    message TEXT
) AS $$
DECLARE
    validation_result RECORD;
    new_session_token VARCHAR(64);
    license_key_id INTEGER;
BEGIN
    -- Validate license key
    SELECT * INTO validation_result FROM validate_license_key(p_license_key);

    IF NOT validation_result.valid THEN
        RETURN QUERY SELECT FALSE, NULL::VARCHAR(64), validation_result.message;
        RETURN;
    END IF;

    -- Check session limits for non-master keys
    IF validation_result.tier_name != 'master' AND
       validation_result.current_sessions >= validation_result.max_concurrent_sessions THEN
        RETURN QUERY SELECT FALSE, NULL::VARCHAR(64),
                           'Maximum concurrent sessions reached for this license'::TEXT;
        RETURN;
    END IF;

    -- Get license key ID
    SELECT id INTO license_key_id FROM license_keys WHERE license_key = p_license_key;

    -- Generate session token
    new_session_token := generate_session_token();

    -- Create new session
    INSERT INTO license_sessions (
        license_key_id, session_token, device_fingerprint, user_agent, ip_address,
        expires_at
    ) VALUES (
        license_key_id, new_session_token, p_device_fingerprint, p_user_agent, p_ip_address,
        CURRENT_TIMESTAMP + (p_session_duration_hours || ' hours')::INTERVAL
    );

    -- Update last used timestamp
    UPDATE license_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = license_key_id;

    RETURN QUERY SELECT TRUE, new_session_token, 'Session created successfully'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to validate session token
CREATE OR REPLACE FUNCTION validate_session_token(p_session_token VARCHAR(64))
RETURNS TABLE(
    valid BOOLEAN,
    license_key_id INTEGER,
    tier_name VARCHAR(50),
    features_enabled JSONB,
    message TEXT
) AS $$
DECLARE
    session_record RECORD;
BEGIN
    -- Get session details with license info
    SELECT ls.license_key_id, ls.is_active, ls.expires_at,
           lt.tier_name, lt.features_enabled
    INTO session_record
    FROM license_sessions ls
    JOIN license_keys lk ON ls.license_key_id = lk.id
    JOIN license_tiers lt ON lk.tier_id = lt.id
    WHERE ls.session_token = p_session_token;

    -- Check if session exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::VARCHAR(50), NULL::JSONB,
                           'Invalid session token'::TEXT;
        RETURN;
    END IF;

    -- Check if session is active
    IF NOT session_record.is_active THEN
        RETURN QUERY SELECT FALSE, session_record.license_key_id, session_record.tier_name,
                           session_record.features_enabled, 'Session is inactive'::TEXT;
        RETURN;
    END IF;

    -- Check if session has expired
    IF session_record.expires_at IS NOT NULL AND session_record.expires_at < CURRENT_TIMESTAMP THEN
        -- Deactivate expired session
        UPDATE license_sessions SET is_active = FALSE WHERE session_token = p_session_token;

        RETURN QUERY SELECT FALSE, session_record.license_key_id, session_record.tier_name,
                           session_record.features_enabled, 'Session has expired'::TEXT;
        RETURN;
    END IF;

    -- Update last activity
    UPDATE license_sessions SET last_activity_at = CURRENT_TIMESTAMP WHERE session_token = p_session_token;

    -- Return validation result
    RETURN QUERY SELECT TRUE, session_record.license_key_id, session_record.tier_name,
                       session_record.features_enabled, 'Session is valid'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to log API usage
CREATE OR REPLACE FUNCTION log_api_usage(
    p_session_token VARCHAR(64),
    p_endpoint VARCHAR(255),
    p_method VARCHAR(10),
    p_request_size INTEGER DEFAULT 0,
    p_response_size INTEGER DEFAULT 0,
    p_response_status INTEGER DEFAULT 200,
    p_processing_time_ms INTEGER DEFAULT 0,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    session_info RECORD;
BEGIN
    -- Get session and license info
    SELECT ls.license_key_id, ls.id as session_id
    INTO session_info
    FROM license_sessions ls
    WHERE ls.session_token = p_session_token AND ls.is_active = TRUE;

    -- Only log if session is valid
    IF FOUND THEN
        INSERT INTO api_usage_logs (
            license_key_id, session_id, endpoint, method,
            request_size, response_size, response_status,
            processing_time_ms, ip_address, user_agent
        ) VALUES (
            session_info.license_key_id, session_info.session_id, p_endpoint, p_method,
            p_request_size, p_response_size, p_response_status,
            p_processing_time_ms, p_ip_address, p_user_agent
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Insert default license tiers
INSERT INTO license_tiers (tier_name, display_name, max_concurrent_sessions, max_api_calls_per_hour, max_api_calls_per_day, features_enabled, price_monthly) VALUES
('evaluation', 'Evaluation License', 1, 10, 50, '{"sentiment": true, "technical": false, "historical": false, "unified": false}', 0.00),
('standard', 'Standard License', 1, 100, 1000, '{"sentiment": true, "technical": true, "historical": true, "unified": false}', 29.99),
('premium', 'Premium License', 3, 500, 5000, '{"sentiment": true, "technical": true, "historical": true, "unified": true}', 99.99),
('master', 'Master License', -1, -1, -1, '{"sentiment": true, "technical": true, "historical": true, "unified": true, "admin": true}', 0.00);

-- Sample query to test functionality
-- SELECT * FROM get_cached_analysis_with_articles('AAPL');
-- SELECT * FROM get_recent_articles('AAPL', 50, 24);
-- SELECT * FROM validate_license_key('your_license_key_here');
-- SELECT * FROM create_license_session('your_license_key_here', 'device123', 'Mozilla/5.0...', '192.168.1.1'::inet);