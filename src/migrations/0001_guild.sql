CREATE TABLE IF NOT EXISTS serenity_guilds (
    snowflake        BIGINT PRIMARY KEY NOT NULL,
    banned           BOOLEAN NOT NULL DEFAULT FALSE,
    counting_prefix  VARCHAR(2000) NOT NULL DEFAULT 'owo',
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    CONSTRAINT serenity_guilds_pkey
        UNIQUE (snowflake)
);


CREATE TABLE IF NOT EXISTS serenity_guild_prefixes (
    snowflake       BIGINT NOT NULL,
    prefix          VARCHAR(2000) NOT NULL,
    CONSTRAINT serenity_guild_prefixes_fkey
        FOREIGN KEY (snowflake)
        REFERENCES serenity_guilds(snowflake)
        ON DELETE CASCADE
);


CREATE OR REPLACE FUNCTION insert_default_prefix() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM serenity_guild_prefixes
        WHERE snowflake = NEW.snowflake
    ) THEN
        INSERT INTO serenity_guild_prefixes (snowflake, prefix)
        VALUES (NEW.snowflake, 's!'), (NEW.snowflake, 's?');
    END IF;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;


DO $$
BEGIN 
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'insert_default_prefix'
    ) THEN
        CREATE TRIGGER insert_default_prefix
        AFTER INSERT ON serenity_guilds
        FOR EACH ROW
        EXECUTE PROCEDURE insert_default_prefix();
    END IF;
END $$;


CREATE TABLE IF NOT EXISTS serenity_guild_emotes (
    snowflake       BIGINT NOT NULL,
    emote_snowflake BIGINT NOT NULL,
    emote_usage     BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT serenity_guild_emotes_fkey
        FOREIGN KEY (snowflake)
        REFERENCES serenity_guilds(snowflake)
        ON DELETE CASCADE
);
