-- Company Symbol Cache Table Schema
-- Stores company symbol, name, and industry information to reduce API calls

-- Create the company information cache table
DROP TABLE IF EXISTS company_info_cache CASCADE;
CREATE TABLE company_info_cache (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT company_info_symbol_check CHECK (LENGTH(symbol) > 0),
    CONSTRAINT company_info_name_check CHECK (LENGTH(company_name) > 0),
    CONSTRAINT company_info_industry_check CHECK (LENGTH(industry) > 0)
);

-- Create indexes for fast lookups
CREATE INDEX idx_company_info_symbol ON company_info_cache(symbol);
CREATE INDEX idx_company_info_industry ON company_info_cache(industry);
CREATE INDEX idx_company_info_last_verified ON company_info_cache(last_verified);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_company_info_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger for updated_at
CREATE TRIGGER update_company_info_updated_at 
    BEFORE UPDATE ON company_info_cache 
    FOR EACH ROW EXECUTE FUNCTION update_company_info_updated_at_column();

-- Function to get company info (checks if update is needed based on age)
CREATE OR REPLACE FUNCTION get_company_info(p_symbol VARCHAR(10), p_max_days INTEGER DEFAULT 30)
RETURNS TABLE(
    symbol VARCHAR(10),
    company_name VARCHAR(255),
    industry VARCHAR(100),
    needs_update BOOLEAN,
    days_old INTEGER,
    last_verified TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    days_since_verified INTEGER;
BEGIN
    RETURN QUERY 
    SELECT 
        cic.symbol,
        cic.company_name,
        cic.industry,
        CASE 
            WHEN EXTRACT(DAYS FROM (NOW() - cic.last_verified)) > p_max_days THEN TRUE
            ELSE FALSE
        END as needs_update,
        EXTRACT(DAYS FROM (NOW() - cic.last_verified))::INTEGER as days_old,
        cic.last_verified
    FROM company_info_cache cic
    WHERE cic.symbol = UPPER(p_symbol);
    
    -- If no row found, return nothing (caller will handle)
    IF NOT FOUND THEN
        RETURN;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to insert or update company info
CREATE OR REPLACE FUNCTION upsert_company_info(
    p_symbol VARCHAR(10),
    p_company_name VARCHAR(255),
    p_industry VARCHAR(100)
) RETURNS BIGINT AS $$
DECLARE
    company_id BIGINT;
BEGIN
    -- Try to update existing record
    UPDATE company_info_cache 
    SET 
        company_name = p_company_name,
        industry = p_industry,
        last_verified = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE symbol = UPPER(p_symbol)
    RETURNING id INTO company_id;
    
    -- If no existing record, insert new one
    IF company_id IS NULL THEN
        INSERT INTO company_info_cache (symbol, company_name, industry)
        VALUES (UPPER(p_symbol), p_company_name, p_industry)
        RETURNING id INTO company_id;
    END IF;
    
    RETURN company_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get all cached companies
CREATE OR REPLACE FUNCTION get_all_cached_companies()
RETURNS TABLE(
    symbol VARCHAR(10),
    company_name VARCHAR(255),
    industry VARCHAR(100),
    days_old INTEGER,
    last_verified TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        cic.symbol,
        cic.company_name,
        cic.industry,
        EXTRACT(DAYS FROM (NOW() - cic.last_verified))::INTEGER as days_old,
        cic.last_verified
    FROM company_info_cache cic
    ORDER BY cic.symbol;
END;
$$ LANGUAGE plpgsql;

-- Function to get companies needing update
CREATE OR REPLACE FUNCTION get_companies_needing_update(p_max_days INTEGER DEFAULT 30)
RETURNS TABLE(
    symbol VARCHAR(10),
    company_name VARCHAR(255),
    industry VARCHAR(100),
    days_old INTEGER,
    last_verified TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        cic.symbol,
        cic.company_name,
        cic.industry,
        EXTRACT(DAYS FROM (NOW() - cic.last_verified))::INTEGER as days_old,
        cic.last_verified
    FROM company_info_cache cic
    WHERE EXTRACT(DAYS FROM (NOW() - cic.last_verified)) > p_max_days
    ORDER BY cic.last_verified ASC;
END;
$$ LANGUAGE plpgsql;

-- View for easy querying
CREATE OR REPLACE VIEW company_cache_status AS
SELECT 
    symbol,
    company_name,
    industry,
    EXTRACT(DAYS FROM (NOW() - last_verified))::INTEGER as days_old,
    CASE 
        WHEN EXTRACT(DAYS FROM (NOW() - last_verified)) > 30 THEN 'NEEDS_UPDATE'
        WHEN EXTRACT(DAYS FROM (NOW() - last_verified)) > 14 THEN 'AGING'
        ELSE 'FRESH'
    END as status,
    last_verified,
    created_at
FROM company_info_cache 
ORDER BY symbol;

-- Sample queries to test functionality
-- SELECT * FROM get_company_info('AAPL');
-- SELECT * FROM get_all_cached_companies();
-- SELECT * FROM get_companies_needing_update(30);
-- SELECT * FROM company_cache_status;