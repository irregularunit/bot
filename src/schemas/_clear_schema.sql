DO $$ DECLARE
    rec RECORD;
BEGIN
    FOR rec IN (
        SELECT tablename from pg_tables 
        WHERE schemaname = current_schema()
    ) LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(rec.tablename) || ' CASCADE';
    END LOOP;
END $$;
