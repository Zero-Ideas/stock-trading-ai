-- Industry Analysis Table Schema
-- Partitioned table for storing industry sentiment analysis results

-- Create the main partitioned industry analysis table
DROP TABLE IF EXISTS industry_analysis_partitioned CASCADE;
CREATE TABLE industry_analysis_partitioned (
    id BIGSERIAL,
    industry VARCHAR(100) NOT NULL,
    company_symbol VARCHAR(10),
    company_name VARCHAR(255),
    overall_sentiment DECIMAL(8,6) NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    confidence_score DECIMAL(8,6) NOT NULL,
    key_trends JSONB,
    reasoning TEXT,
    sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT industry_analysis_sentiment_check CHECK (overall_sentiment >= -1.0 AND overall_sentiment <= 1.0),
    CONSTRAINT industry_analysis_confidence_check CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
) PARTITION BY LIST (industry);

-- Create partitions for each industry
CREATE TABLE industry_analysis_technology PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Technology');
CREATE TABLE industry_analysis_semiconductor PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Semiconductor');
CREATE TABLE industry_analysis_healthcare PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Healthcare');
CREATE TABLE industry_analysis_finance PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Finance');
CREATE TABLE industry_analysis_retail PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Retail');
CREATE TABLE industry_analysis_manufacturing PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Manufacturing');
CREATE TABLE industry_analysis_energy PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Energy');
CREATE TABLE industry_analysis_consumer_goods PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Consumer Goods');
CREATE TABLE industry_analysis_real_estate PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Real Estate');
CREATE TABLE industry_analysis_telecommunications PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Telecommunications');
CREATE TABLE industry_analysis_utilities PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Utilities');
CREATE TABLE industry_analysis_transportation PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Transportation');
CREATE TABLE industry_analysis_hospitality PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Hospitality');
CREATE TABLE industry_analysis_construction PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Construction');
CREATE TABLE industry_analysis_education PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Education');
CREATE TABLE industry_analysis_government PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Government');
CREATE TABLE industry_analysis_agriculture PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Agriculture');
CREATE TABLE industry_analysis_media_entertainment PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Media & Entertainment');
CREATE TABLE industry_analysis_professional_services PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Professional Services');
CREATE TABLE industry_analysis_pharmaceuticals PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Pharmaceuticals');
CREATE TABLE industry_analysis_biotechnology PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Biotechnology');
CREATE TABLE industry_analysis_automotive PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Automotive');
CREATE TABLE industry_analysis_aerospace_defense PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Aerospace & Defense');
CREATE TABLE industry_analysis_insurance PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Insurance');
CREATE TABLE industry_analysis_food_beverage PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Food & Beverage');
CREATE TABLE industry_analysis_chemicals PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Chemicals');
CREATE TABLE industry_analysis_mining_metals PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Mining & Metals');
CREATE TABLE industry_analysis_logistics_shipping PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Logistics & Shipping');
CREATE TABLE industry_analysis_ecommerce PARTITION OF industry_analysis_partitioned FOR VALUES IN ('E-commerce');
CREATE TABLE industry_analysis_it_services PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Information Technology Services');
CREATE TABLE industry_analysis_renewable_energy PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Renewable Energy');
CREATE TABLE industry_analysis_travel_tourism PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Travel & Tourism');
CREATE TABLE industry_analysis_nonprofit_ngos PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Nonprofit & NGOs');
CREATE TABLE industry_analysis_sports_recreation PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Sports & Recreation');
CREATE TABLE industry_analysis_fashion_apparel PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Fashion & Apparel');
CREATE TABLE industry_analysis_legal_services PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Legal Services');
CREATE TABLE industry_analysis_advertising_marketing PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Advertising & Marketing');
CREATE TABLE industry_analysis_semiconductor_equipment PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Semiconductor Equipment');
CREATE TABLE industry_analysis_internet_online PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Internet & Online Services');
CREATE TABLE industry_analysis_electronics PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Electronics');
CREATE TABLE industry_analysis_luxury_goods PARTITION OF industry_analysis_partitioned FOR VALUES IN ('Luxury Goods');

-- Create indexes on the main partitioned table
CREATE INDEX idx_industry_analysis_industry ON industry_analysis_partitioned(industry);
CREATE INDEX idx_industry_analysis_created_at ON industry_analysis_partitioned(created_at DESC);
CREATE INDEX idx_industry_analysis_sentiment ON industry_analysis_partitioned(overall_sentiment DESC);
CREATE INDEX idx_industry_analysis_confidence ON industry_analysis_partitioned(confidence_score DESC);
CREATE INDEX idx_industry_analysis_symbol ON industry_analysis_partitioned(company_symbol);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_industry_analysis_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger for updated_at
CREATE TRIGGER update_industry_analysis_updated_at 
    BEFORE UPDATE ON industry_analysis_partitioned 
    FOR EACH ROW EXECUTE FUNCTION update_industry_analysis_updated_at_column();

-- Function to insert industry analysis data
CREATE OR REPLACE FUNCTION insert_industry_analysis(
    p_industry VARCHAR(100),
    p_company_symbol VARCHAR(10),
    p_company_name VARCHAR(255),
    p_overall_sentiment DECIMAL(8,6),
    p_sentiment_label VARCHAR(20),
    p_confidence_score DECIMAL(8,6),
    p_key_trends JSONB,
    p_reasoning TEXT,
    p_sources JSONB
) RETURNS BIGINT AS $$
DECLARE
    inserted_id BIGINT;
BEGIN
    INSERT INTO industry_analysis_partitioned (
        industry, company_symbol, company_name, overall_sentiment,
        sentiment_label, confidence_score, key_trends, reasoning, sources
    ) VALUES (
        p_industry, p_company_symbol, p_company_name, p_overall_sentiment,
        p_sentiment_label, p_confidence_score, p_key_trends, p_reasoning, p_sources
    ) RETURNING id INTO inserted_id;
    
    RETURN inserted_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get recent analysis by industry
CREATE OR REPLACE FUNCTION get_recent_industry_analysis(p_industry VARCHAR(100), p_limit INTEGER DEFAULT 10)
RETURNS TABLE(
    id BIGINT,
    industry VARCHAR(100),
    company_symbol VARCHAR(10),
    company_name VARCHAR(255),
    overall_sentiment DECIMAL(8,6),
    sentiment_label VARCHAR(20),
    confidence_score DECIMAL(8,6),
    key_trends JSONB,
    reasoning TEXT,
    sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        ia.id,
        ia.industry,
        ia.company_symbol,
        ia.company_name,
        ia.overall_sentiment,
        ia.sentiment_label,
        ia.confidence_score,
        ia.key_trends,
        ia.reasoning,
        ia.sources,
        ia.created_at
    FROM industry_analysis_partitioned ia
    WHERE ia.industry = p_industry
    ORDER BY ia.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- View for latest analysis per industry
CREATE OR REPLACE VIEW latest_industry_analysis AS
SELECT DISTINCT ON (industry) 
    id,
    industry,
    company_symbol,
    company_name,
    overall_sentiment,
    sentiment_label,
    confidence_score,
    created_at
FROM industry_analysis_partitioned 
ORDER BY industry, created_at DESC;