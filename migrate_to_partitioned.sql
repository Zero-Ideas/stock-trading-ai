-- Migration script to move data from per-symbol tables to partitioned table
-- Run this after applying database_schema_partitioned.sql

DO $$
DECLARE
    symbol_table RECORD;
    migration_count INTEGER := 0;
    total_migrated INTEGER := 0;
    error_count INTEGER := 0;
    duplicate_count INTEGER := 0;
BEGIN
    RAISE NOTICE 'Starting migration from per-symbol tables to partitioned table...';
    
    -- Loop through all existing articles_* tables
    FOR symbol_table IN 
        SELECT table_name, replace(table_name, 'articles_', '') as symbol
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'articles_%'
        AND table_name != 'articles_partitioned'
        ORDER BY table_name
    LOOP
        BEGIN
            RAISE NOTICE 'Migrating table: % (symbol: %)', symbol_table.table_name, symbol_table.symbol;
            
            -- Get count of records in the source table
            EXECUTE format('SELECT COUNT(*) FROM %I', symbol_table.table_name) INTO migration_count;
            RAISE NOTICE '  Records to migrate: %', migration_count;
            
            -- Migrate data using dynamic SQL
            EXECUTE format('
                INSERT INTO articles_partitioned (
                    symbol, title, full_text, raw_extracted_text, extraction_successful,
                    source, url, url_hash, article_timestamp, polarity, compound,
                    sentiment_label, text_length, extracted_length, enhancement_ratio,
                    created_at, updated_at
                )
                SELECT 
                    %L,
                    title,
                    full_text,
                    raw_extracted_text,
                    extraction_successful,
                    source,
                    url,
                    url_hash,
                    article_timestamp,
                    polarity,
                    compound,
                    sentiment_label,
                    text_length,
                    extracted_length,
                    enhancement_ratio,
                    created_at,
                    updated_at
                FROM %I
                ON CONFLICT (url_hash, symbol) DO NOTHING',
                symbol_table.symbol,
                symbol_table.table_name
            );
            
            -- Get the actual number of migrated records (excluding duplicates)
            GET DIAGNOSTICS migration_count = ROW_COUNT;
            total_migrated := total_migrated + migration_count;
            
            RAISE NOTICE '  Successfully migrated: % records', migration_count;
            
        EXCEPTION
            WHEN OTHERS THEN
                error_count := error_count + 1;
                RAISE NOTICE '  ERROR migrating table %: %', symbol_table.table_name, SQLERRM;
                CONTINUE;
        END;
    END LOOP;
    
    RAISE NOTICE 'Migration completed!';
    RAISE NOTICE '  Total records migrated: %', total_migrated;
    RAISE NOTICE '  Tables with errors: %', error_count;
    
    -- Show summary statistics
    RAISE NOTICE '';
    RAISE NOTICE 'Post-migration statistics:';
    
    -- Count articles by symbol in partitioned table
    FOR symbol_table IN 
        SELECT symbol, COUNT(*) as count
        FROM articles_partitioned 
        GROUP BY symbol 
        ORDER BY symbol
    LOOP
        RAISE NOTICE '  %: % articles', symbol_table.symbol, symbol_table.count;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Migration verification:';
    RAISE NOTICE '  Total articles in partitioned table: %', (SELECT COUNT(*) FROM articles_partitioned);
    RAISE NOTICE '  Unique symbols: %', (SELECT COUNT(DISTINCT symbol) FROM articles_partitioned);
    RAISE NOTICE '  Unique URLs: %', (SELECT COUNT(DISTINCT url_hash) FROM articles_partitioned);
    
END $$;