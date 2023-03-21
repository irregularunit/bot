/*
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
 */

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
