/*
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
 */

CREATE TABLE IF NOT EXISTS users (
    uid BIGINT PRIMARY KEY NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC' CHECK (timezone <> ''),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL,
    CONSTRAINT users_uid_check CHECK (uid > 0)
);

CREATE TABLE IF NOT EXISTS presence_history (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    uid BIGINT NOT NULL,
    status TEXT NOT NULL,
    status_before TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL
);

CREATE TABLE IF NOT EXISTS item_history (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    uid BIGINT NOT NULL,
    item_type TEXT NOT NULL,
    item_value TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL,
    CONSTRAINT item_history_item_type_check CHECK (item_type IN ('avatar', 'discriminator', 'name'))
);

CREATE TABLE IF NOT EXISTS avatar_history (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    uid BIGINT NOT NULL,
    format TEXT NOT NULL,
    avatar BYTEA NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL
);

CREATE OR REPLACE FUNCTION insert_avatar_history_item(p_user_id bigint, p_format text, p_avatar bytea)
RETURNS void AS $$
BEGIN
    IF NOT EXISTS (
        WITH last_avatar AS (
            SELECT avatar FROM avatar_history
            WHERE uid = p_user_id
            ORDER BY changed_at DESC
            LIMIT 1
        )
        SELECT 1 FROM last_avatar WHERE avatar = p_avatar
    ) THEN
        INSERT INTO avatar_history (uid, format, avatar) VALUES (p_user_id, p_format, p_avatar);
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION limit_avatar_history()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM avatar_history
    WHERE uid = NEW.uid
    AND changed_at < (
        SELECT changed_at FROM avatar_history
        WHERE uid = NEW.uid
        ORDER BY changed_at DESC
        OFFSET 24
        LIMIT 1
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'limit_avatar_history') THEN
        CREATE TRIGGER limit_avatar_history
        AFTER INSERT ON avatar_history
        FOR EACH ROW EXECUTE PROCEDURE limit_avatar_history();
    END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS guilds (
    gid BIGINT PRIMARY KEY NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL,
    owo_prefix TEXT NOT NULL DEFAULT 'owo',
    owo_counting BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT guilds_gid_check CHECK (gid > 0)
);

CREATE TABLE IF NOT EXISTS owo_counting (
  id BIGSERIAL PRIMARY KEY NOT NULL,
  uid BIGINT NOT NULL,
  word TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  CONSTRAINT owo_counting_word_check CHECK (word IN ('hunt', 'battle', 'owo')) 
);

CREATE TABLE IF NOT EXISTS guild_prefixes (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    gid BIGINT NOT NULL,
    prefix TEXT NOT NULL,
    CONSTRAINT guild_prefixes_gid_fk FOREIGN KEY (gid) REFERENCES guilds(gid) ON DELETE CASCADE,
    CONSTRAINT guild_prefixes_prefix_pk UNIQUE (gid, prefix),
    CONSTRAINT guild_prefixex_prefix_empty_check CHECK (prefix <> '')
);

CREATE OR REPLACE FUNCTION insert_default_prefix()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM guild_prefixes WHERE gid = NEW.gid) THEN
        INSERT INTO guild_prefixes (gid, prefix)
        SELECT NEW.gid, prefix
        FROM (
            SELECT 'uwu' AS prefix
            UNION ALL SELECT 'uwu '
        ) AS default_prefixes;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'insert_default_prefix') THEN
        CREATE TRIGGER insert_default_prefix
        AFTER INSERT ON guilds
        FOR EACH ROW EXECUTE PROCEDURE insert_default_prefix();
    END IF;
END;
$$;
