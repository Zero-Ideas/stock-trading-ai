-- PostgreSQL Schema for Stock Market Data (Day, Hour, Minute)
-- Partitioned tables by symbol for efficient querying and indexing

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drop existing tables if they exist
DROP TABLE IF EXISTS stock_data_day CASCADE;
DROP TABLE IF EXISTS stock_data_hour CASCADE; 
DROP TABLE IF EXISTS stock_data_minute CASCADE;

-- Create partitioned table for daily stock data
CREATE TABLE stock_data_day (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    price_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(12,6) NOT NULL,
    high DECIMAL(12,6) NOT NULL,
    low DECIMAL(12,6) NOT NULL,
    close DECIMAL(12,6) NOT NULL,
    volume BIGINT,
    trade_count BIGINT,
    vwap DECIMAL(12,6),
    original BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT stock_data_day_symbol_timestamp_unique UNIQUE (symbol, price_timestamp),
    CONSTRAINT stock_data_day_price_check CHECK (open > 0 AND high > 0 AND low > 0 AND close > 0),
    CONSTRAINT stock_data_day_volume_check CHECK (volume >= 0)
) PARTITION BY HASH (symbol);

-- Create partitioned table for hourly stock data
CREATE TABLE stock_data_hour (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    price_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(12,6) NOT NULL,
    high DECIMAL(12,6) NOT NULL,
    low DECIMAL(12,6) NOT NULL,
    close DECIMAL(12,6) NOT NULL,
    volume BIGINT,
    trade_count BIGINT,
    vwap DECIMAL(12,6),
    original BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT stock_data_hour_symbol_timestamp_unique UNIQUE (symbol, price_timestamp),
    CONSTRAINT stock_data_hour_price_check CHECK (open > 0 AND high > 0 AND low > 0 AND close > 0),
    CONSTRAINT stock_data_hour_volume_check CHECK (volume >= 0)
) PARTITION BY HASH (symbol);

-- Create partitioned table for minute stock data
CREATE TABLE stock_data_minute (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    price_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(12,6) NOT NULL,
    high DECIMAL(12,6) NOT NULL,
    low DECIMAL(12,6) NOT NULL,
    close DECIMAL(12,6) NOT NULL,
    volume BIGINT,
    trade_count BIGINT,
    vwap DECIMAL(12,6),
    original BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT stock_data_minute_symbol_timestamp_unique UNIQUE (symbol, price_timestamp),
    CONSTRAINT stock_data_minute_price_check CHECK (open > 0 AND high > 0 AND low > 0 AND close > 0),
    CONSTRAINT stock_data_minute_volume_check CHECK (volume >= 0)
) PARTITION BY HASH (symbol);

-- Create partitions for daily data (16 partitions)
CREATE TABLE stock_data_day_p0 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 0);
CREATE TABLE stock_data_day_p1 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 1);
CREATE TABLE stock_data_day_p2 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 2);
CREATE TABLE stock_data_day_p3 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 3);
CREATE TABLE stock_data_day_p4 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 4);
CREATE TABLE stock_data_day_p5 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 5);
CREATE TABLE stock_data_day_p6 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 6);
CREATE TABLE stock_data_day_p7 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 7);
CREATE TABLE stock_data_day_p8 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 8);
CREATE TABLE stock_data_day_p9 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 9);
CREATE TABLE stock_data_day_p10 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 10);
CREATE TABLE stock_data_day_p11 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 11);
CREATE TABLE stock_data_day_p12 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 12);
CREATE TABLE stock_data_day_p13 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 13);
CREATE TABLE stock_data_day_p14 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 14);
CREATE TABLE stock_data_day_p15 PARTITION OF stock_data_day FOR VALUES WITH (modulus 16, remainder 15);

-- Create partitions for hourly data (16 partitions)
CREATE TABLE stock_data_hour_p0 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 0);
CREATE TABLE stock_data_hour_p1 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 1);
CREATE TABLE stock_data_hour_p2 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 2);
CREATE TABLE stock_data_hour_p3 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 3);
CREATE TABLE stock_data_hour_p4 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 4);
CREATE TABLE stock_data_hour_p5 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 5);
CREATE TABLE stock_data_hour_p6 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 6);
CREATE TABLE stock_data_hour_p7 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 7);
CREATE TABLE stock_data_hour_p8 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 8);
CREATE TABLE stock_data_hour_p9 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 9);
CREATE TABLE stock_data_hour_p10 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 10);
CREATE TABLE stock_data_hour_p11 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 11);
CREATE TABLE stock_data_hour_p12 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 12);
CREATE TABLE stock_data_hour_p13 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 13);
CREATE TABLE stock_data_hour_p14 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 14);
CREATE TABLE stock_data_hour_p15 PARTITION OF stock_data_hour FOR VALUES WITH (modulus 16, remainder 15);

-- Create partitions for minute data (16 partitions)
CREATE TABLE stock_data_minute_p0 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 0);
CREATE TABLE stock_data_minute_p1 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 1);
CREATE TABLE stock_data_minute_p2 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 2);
CREATE TABLE stock_data_minute_p3 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 3);
CREATE TABLE stock_data_minute_p4 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 4);
CREATE TABLE stock_data_minute_p5 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 5);
CREATE TABLE stock_data_minute_p6 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 6);
CREATE TABLE stock_data_minute_p7 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 7);
CREATE TABLE stock_data_minute_p8 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 8);
CREATE TABLE stock_data_minute_p9 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 9);
CREATE TABLE stock_data_minute_p10 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 10);
CREATE TABLE stock_data_minute_p11 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 11);
CREATE TABLE stock_data_minute_p12 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 12);
CREATE TABLE stock_data_minute_p13 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 13);
CREATE TABLE stock_data_minute_p14 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 14);
CREATE TABLE stock_data_minute_p15 PARTITION OF stock_data_minute FOR VALUES WITH (modulus 16, remainder 15);

-- Create indexes for daily data (automatically applied to all partitions)
CREATE INDEX idx_stock_data_day_symbol ON stock_data_day(symbol);
CREATE INDEX idx_stock_data_day_timestamp ON stock_data_day(price_timestamp DESC);
CREATE INDEX idx_stock_data_day_symbol_timestamp ON stock_data_day(symbol, price_timestamp DESC);
CREATE INDEX idx_stock_data_day_volume ON stock_data_day(volume DESC);

-- Create indexes for hourly data
CREATE INDEX idx_stock_data_hour_symbol ON stock_data_hour(symbol);
CREATE INDEX idx_stock_data_hour_timestamp ON stock_data_hour(price_timestamp DESC);
CREATE INDEX idx_stock_data_hour_symbol_timestamp ON stock_data_hour(symbol, price_timestamp DESC);
CREATE INDEX idx_stock_data_hour_volume ON stock_data_hour(volume DESC);

-- Create indexes for minute data
CREATE INDEX idx_stock_data_minute_symbol ON stock_data_minute(symbol);
CREATE INDEX idx_stock_data_minute_timestamp ON stock_data_minute(price_timestamp DESC);
CREATE INDEX idx_stock_data_minute_symbol_timestamp ON stock_data_minute(symbol, price_timestamp DESC);
CREATE INDEX idx_stock_data_minute_volume ON stock_data_minute(volume DESC);

-- Utility functions for stock data

-- Function to get latest stock data by symbol and timeframe
CREATE OR REPLACE FUNCTION get_latest_stock_data(p_symbol VARCHAR(10), p_timeframe VARCHAR(10), p_limit INTEGER DEFAULT 100)
RETURNS TABLE(
    symbol VARCHAR(10),
    price_timestamp TIMESTAMP WITH TIME ZONE,
    open DECIMAL(12,6),
    high DECIMAL(12,6),
    low DECIMAL(12,6),
    close DECIMAL(12,6),
    volume BIGINT,
    trade_count BIGINT,
    vwap DECIMAL(12,6),
    original BOOLEAN
) AS $$
BEGIN
    IF p_timeframe = 'day' THEN
        RETURN QUERY
        SELECT s.symbol, s.price_timestamp, s.open, s.high, s.low, s.close, s.volume, s.trade_count, s.vwap, s.original
        FROM stock_data_day s
        WHERE s.symbol = p_symbol
        ORDER BY s.price_timestamp DESC
        LIMIT p_limit;
    ELSIF p_timeframe = 'hour' THEN
        RETURN QUERY
        SELECT s.symbol, s.price_timestamp, s.open, s.high, s.low, s.close, s.volume, s.trade_count, s.vwap, s.original
        FROM stock_data_hour s
        WHERE s.symbol = p_symbol
        ORDER BY s.price_timestamp DESC
        LIMIT p_limit;
    ELSIF p_timeframe = 'minute' THEN
        RETURN QUERY
        SELECT s.symbol, s.price_timestamp, s.open, s.high, s.low, s.close, s.volume, s.trade_count, s.vwap, s.original
        FROM stock_data_minute s
        WHERE s.symbol = p_symbol
        ORDER BY s.price_timestamp DESC
        LIMIT p_limit;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to get stock data count by symbol and timeframe
CREATE OR REPLACE FUNCTION get_stock_data_count(p_symbol VARCHAR(10), p_timeframe VARCHAR(10))
RETURNS INTEGER AS $$
DECLARE
    data_count INTEGER;
BEGIN
    IF p_timeframe = 'day' THEN
        SELECT COUNT(*) INTO data_count FROM stock_data_day WHERE symbol = p_symbol;
    ELSIF p_timeframe = 'hour' THEN
        SELECT COUNT(*) INTO data_count FROM stock_data_hour WHERE symbol = p_symbol;
    ELSIF p_timeframe = 'minute' THEN
        SELECT COUNT(*) INTO data_count FROM stock_data_minute WHERE symbol = p_symbol;
    ELSE
        data_count := 0;
    END IF;
    
    RETURN data_count;
END;
$$ LANGUAGE plpgsql;

-- Function to bulk insert stock data with conflict resolution
CREATE OR REPLACE FUNCTION bulk_insert_stock_data(
    p_timeframe VARCHAR(10),
    p_data JSONB
) RETURNS INTEGER AS $$
DECLARE
    inserted_count INTEGER := 0;
    data_row JSONB;
BEGIN
    FOR data_row IN SELECT * FROM jsonb_array_elements(p_data)
    LOOP
        BEGIN
            IF p_timeframe = 'day' THEN
                INSERT INTO stock_data_day (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                VALUES (
                    (data_row->>'symbol')::VARCHAR(10),
                    (data_row->>'price_timestamp')::TIMESTAMP WITH TIME ZONE,
                    (data_row->>'open')::DECIMAL(12,6),
                    (data_row->>'high')::DECIMAL(12,6),
                    (data_row->>'low')::DECIMAL(12,6),
                    (data_row->>'close')::DECIMAL(12,6),
                    (data_row->>'volume')::BIGINT,
                    (data_row->>'trade_count')::BIGINT,
                    (data_row->>'vwap')::DECIMAL(12,6),
                    (data_row->>'original')::BOOLEAN
                );
            ELSIF p_timeframe = 'hour' THEN
                INSERT INTO stock_data_hour (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                VALUES (
                    (data_row->>'symbol')::VARCHAR(10),
                    (data_row->>'price_timestamp')::TIMESTAMP WITH TIME ZONE,
                    (data_row->>'open')::DECIMAL(12,6),
                    (data_row->>'high')::DECIMAL(12,6),
                    (data_row->>'low')::DECIMAL(12,6),
                    (data_row->>'close')::DECIMAL(12,6),
                    (data_row->>'volume')::BIGINT,
                    (data_row->>'trade_count')::BIGINT,
                    (data_row->>'vwap')::DECIMAL(12,6),
                    (data_row->>'original')::BOOLEAN
                );
            ELSIF p_timeframe = 'minute' THEN
                INSERT INTO stock_data_minute (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                VALUES (
                    (data_row->>'symbol')::VARCHAR(10),
                    (data_row->>'price_timestamp')::TIMESTAMP WITH TIME ZONE,
                    (data_row->>'open')::DECIMAL(12,6),
                    (data_row->>'high')::DECIMAL(12,6),
                    (data_row->>'low')::DECIMAL(12,6),
                    (data_row->>'close')::DECIMAL(12,6),
                    (data_row->>'volume')::BIGINT,
                    (data_row->>'trade_count')::BIGINT,
                    (data_row->>'vwap')::DECIMAL(12,6),
                    (data_row->>'original')::BOOLEAN
                );
            END IF;
            
            inserted_count := inserted_count + 1;
        EXCEPTION
            WHEN unique_violation THEN
                -- Skip duplicate entries
                CONTINUE;
        END;
    END LOOP;
    
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;

-- Views for easy access to recent data
CREATE OR REPLACE VIEW recent_daily_data AS
SELECT DISTINCT ON (symbol) 
    symbol,
    price_timestamp,
    open,
    high,
    low,
    close,
    volume,
    trade_count,
    vwap,
    original
FROM stock_data_day
ORDER BY symbol, price_timestamp DESC;

CREATE OR REPLACE VIEW recent_hourly_data AS
SELECT DISTINCT ON (symbol) 
    symbol,
    price_timestamp,
    open,
    high,
    low,
    close,
    volume,
    trade_count,
    vwap,
    original
FROM stock_data_hour
ORDER BY symbol, price_timestamp DESC;

CREATE OR REPLACE VIEW recent_minute_data AS
SELECT DISTINCT ON (symbol) 
    symbol,
    price_timestamp,
    open,
    high,
    low,
    close,
    volume,
    trade_count,
    vwap,
    original
FROM stock_data_minute
ORDER BY symbol, price_timestamp DESC;

-- Sample queries:
-- SELECT * FROM get_latest_stock_data('AAPL', 'day', 30);
-- SELECT get_stock_data_count('AAPL', 'minute');
-- SELECT * FROM recent_daily_data WHERE symbol = 'AAPL';