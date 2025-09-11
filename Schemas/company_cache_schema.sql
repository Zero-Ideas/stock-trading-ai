-- Company Information Cache Table Schema
-- Enhanced schema with complete company information for better search results and industry analysis
-- Uses updated_at instead of last_verified for consistency with main database schema

-- Create the company information cache table
DROP TABLE IF EXISTS company_info_cache CASCADE;
CREATE TABLE company_info_cache (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(500),  -- Full official company name (e.g., "NVIDIA Corporation")
    common_name VARCHAR(255),   -- Common/short name for searches (e.g., "NVIDIA")
    industry VARCHAR(255),      -- Industry classification for industry sentiment analyzer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT company_info_symbol_check CHECK (LENGTH(symbol) > 0)
);

-- Create indexes for fast lookups and performance
CREATE INDEX idx_company_info_cache_symbol ON company_info_cache(symbol);
CREATE INDEX idx_company_info_cache_updated_at ON company_info_cache(updated_at DESC);
CREATE INDEX idx_company_info_cache_industry ON company_info_cache(industry);
CREATE INDEX idx_company_info_cache_common_name ON company_info_cache(common_name);

-- Function to update the updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at timestamp on updates
CREATE TRIGGER update_company_info_cache_updated_at 
    BEFORE UPDATE ON company_info_cache 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enhanced function to get company info with age check (using updated_at)
CREATE OR REPLACE FUNCTION get_company_info(p_symbol VARCHAR(10), p_max_days INTEGER DEFAULT 30)
RETURNS TABLE(
    symbol VARCHAR(10),
    company_name VARCHAR(500),
    common_name VARCHAR(255),
    industry VARCHAR(255),
    needs_update BOOLEAN,
    days_old INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    days_since_updated INTEGER;
BEGIN
    RETURN QUERY 
    SELECT 
        cic.symbol,
        cic.company_name,
        cic.common_name,
        cic.industry,
        CASE 
            WHEN EXTRACT(DAYS FROM (NOW() - cic.updated_at)) > p_max_days THEN TRUE
            ELSE FALSE
        END as needs_update,
        EXTRACT(DAYS FROM (NOW() - cic.updated_at))::INTEGER as days_old,
        cic.updated_at
    FROM company_info_cache cic
    WHERE cic.symbol = UPPER(p_symbol);
    
    -- If no row found, return nothing (caller will handle)
    IF NOT FOUND THEN
        RETURN;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Enhanced function to insert or update complete company info
CREATE OR REPLACE FUNCTION upsert_company_info(
    p_symbol VARCHAR(10),
    p_company_name VARCHAR(500) DEFAULT NULL,
    p_common_name VARCHAR(255) DEFAULT NULL,
    p_industry VARCHAR(255) DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    company_id INTEGER;
BEGIN
    -- Try to update existing record (only update non-null values)
    UPDATE company_info_cache 
    SET 
        company_name = COALESCE(p_company_name, company_name),
        common_name = COALESCE(p_common_name, common_name),
        industry = COALESCE(p_industry, industry),
        updated_at = CURRENT_TIMESTAMP
    WHERE symbol = UPPER(p_symbol)
    RETURNING id INTO company_id;
    
    -- If no existing record, insert new one
    IF company_id IS NULL THEN
        INSERT INTO company_info_cache (symbol, company_name, common_name, industry)
        VALUES (UPPER(p_symbol), p_company_name, p_common_name, p_industry)
        RETURNING id INTO company_id;
    END IF;
    
    RETURN company_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get all cached companies with complete info
CREATE OR REPLACE FUNCTION get_all_cached_companies()
RETURNS TABLE(
    symbol VARCHAR(10),
    company_name VARCHAR(500),
    common_name VARCHAR(255),
    industry VARCHAR(255),
    days_old INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        cic.symbol,
        cic.company_name,
        cic.common_name,
        cic.industry,
        EXTRACT(DAYS FROM (NOW() - cic.updated_at))::INTEGER as days_old,
        cic.updated_at
    FROM company_info_cache cic
    ORDER BY cic.symbol;
END;
$$ LANGUAGE plpgsql;

-- Function to get companies needing update (based on updated_at age)
CREATE OR REPLACE FUNCTION get_companies_needing_update(p_max_days INTEGER DEFAULT 30)
RETURNS TABLE(
    symbol VARCHAR(10),
    company_name VARCHAR(500),
    common_name VARCHAR(255),
    industry VARCHAR(255),
    days_old INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        cic.symbol,
        cic.company_name,
        cic.common_name,
        cic.industry,
        EXTRACT(DAYS FROM (NOW() - cic.updated_at))::INTEGER as days_old,
        cic.updated_at
    FROM company_info_cache cic
    WHERE EXTRACT(DAYS FROM (NOW() - cic.updated_at)) > p_max_days
    ORDER BY cic.updated_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to get companies by industry
CREATE OR REPLACE FUNCTION get_companies_by_industry(p_industry VARCHAR(255))
RETURNS TABLE(
    symbol VARCHAR(10),
    company_name VARCHAR(500),
    common_name VARCHAR(255),
    industry VARCHAR(255),
    days_old INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        cic.symbol,
        cic.company_name,
        cic.common_name,
        cic.industry,
        EXTRACT(DAYS FROM (NOW() - cic.updated_at))::INTEGER as days_old,
        cic.updated_at
    FROM company_info_cache cic
    WHERE cic.industry ILIKE '%' || p_industry || '%'
    ORDER BY cic.symbol;
END;
$$ LANGUAGE plpgsql;

-- Enhanced view for easy querying with complete information
CREATE OR REPLACE VIEW company_cache_status AS
SELECT 
    symbol,
    company_name,
    common_name,
    industry,
    EXTRACT(DAYS FROM (NOW() - updated_at))::INTEGER as days_old,
    CASE 
        WHEN EXTRACT(DAYS FROM (NOW() - updated_at)) > 30 THEN 'NEEDS_UPDATE'
        WHEN EXTRACT(DAYS FROM (NOW() - updated_at)) > 14 THEN 'AGING'
        ELSE 'FRESH'
    END as status,
    updated_at,
    created_at
FROM company_info_cache 
ORDER BY symbol;

-- Enhanced view for industry analysis
CREATE OR REPLACE VIEW companies_by_industry AS
SELECT 
    industry,
    COUNT(*) as company_count,
    ARRAY_AGG(symbol ORDER BY symbol) as symbols,
    ARRAY_AGG(common_name ORDER BY symbol) as company_names,
    AVG(EXTRACT(DAYS FROM (NOW() - updated_at))) as avg_days_old
FROM company_info_cache 
WHERE industry IS NOT NULL
GROUP BY industry
ORDER BY company_count DESC, industry;

-- Sample usage queries:
-- Basic company lookup:
-- SELECT * FROM get_company_info('NVDA');

-- Get all companies:
-- SELECT * FROM get_all_cached_companies();

-- Get companies needing update (older than 30 days):
-- SELECT * FROM get_companies_needing_update(30);

-- Get companies by industry:
-- SELECT * FROM get_companies_by_industry('Semiconductors');

-- Check cache status:
-- SELECT * FROM company_cache_status;

-- View industry distribution:
-- SELECT * FROM companies_by_industry;

-- Insert/update company info:
-- SELECT upsert_company_info('NVDA', 'NVIDIA Corporation', 'NVIDIA', 'Semiconductors');
-- SELECT upsert_company_info('TSLA', 'Tesla, Inc.', 'Tesla', 'Electric Vehicles');
-- SELECT upsert_company_info('AAPL', 'Apple Inc.', 'Apple', 'Consumer Electronics');
-- SELECT upsert_company_info('JPM', 'JPMorgan Chase & Co.', 'JPMorgan', 'Banking');

-- Example query to find all tech companies:
-- SELECT symbol, common_name FROM company_info_cache 
-- WHERE industry IN ('Technology', 'Semiconductors', 'Software', 'Consumer Electronics')
-- ORDER BY symbol;