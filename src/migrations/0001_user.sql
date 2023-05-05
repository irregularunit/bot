CREATE TABLE IF NOT EXISTS serenity_users (
    snowflake BIGINT PRIMARY KEY NOT NULL,
    timezone VARCHAR(255) NOT NULL DEFAULT 'UTC',
    locale VARCHAR(255) NOT NULL DEFAULT 'en_US',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    emoji_server_snowflake BIGINT NOT NULL DEFAULT 0,
    banned BOOLEAN NOT NULL DEFAULT FALSE,
    pronouns VARCHAR(255) NOT NULL DEFAULT 'they/them',
    CONSTRAINT serenity_users_pkey UNIQUE (snowflake)
);

CREATE OR REPLACE FUNCTION set_default_settings() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM serenity_user_settings
        WHERE snowflake = NEW.snowflake
    ) THEN
        INSERT INTO serenity_user_settings (snowflake) VALUES (NEW.snowflake);
    END IF;
    RETURN NEW;
END $$ 
LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'set_default_settings'
    ) THEN
        CREATE TRIGGER set_default_settings
        AFTER INSERT ON serenity_users
        FOR EACH ROW
        EXECUTE PROCEDURE set_default_settings();
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS serenity_user_settings (
    snowflake BIGINT NOT NULL,
    counter_message VARCHAR(2000) NOT NULL DEFAULT 'Your cooldown is up!',
    hunt_battle_message VARCHAR(2000) NOT NULL DEFAULT 'You hunt/battle cooldown is up!',
    CONSTRAINT serenity_user_settings_fkey FOREIGN KEY (snowflake) REFERENCES serenity_users(snowflake) ON DELETE CASCADE,
    CONSTRAINT serenity_user_settings_pkey UNIQUE (snowflake)
);

CREATE TABLE IF NOT EXISTS serenity_user_avatars (
    snowflake BIGINT NOT NULL,
    uuid BIGINT NOT NULL,
    mime_format VARCHAR(255) NOT NULL,
    avatar_location TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    CONSTRAINT serenity_user_avatars_fkey FOREIGN KEY (snowflake) REFERENCES serenity_users(snowflake) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS serenity_user_history (
    snowflake BIGINT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    item_value TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    CONSTRAINT serenity_user_history_fkey FOREIGN KEY (snowflake) REFERENCES serenity_users(snowflake) ON DELETE CASCADE
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'serenity_presence_type'
    ) THEN
        CREATE TYPE serenity_presence_type AS ENUM (
            'online',
            'idle',
            'dnd',
            'offline'
        );
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS serenity_user_presence (
    snowflake BIGINT NOT NULL,
    status serenity_presence_type NOT NULL DEFAULT 'offline',
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    CONSTRAINT serenity_user_presence_fkey FOREIGN KEY (snowflake) REFERENCES serenity_users(snowflake) ON DELETE CASCADE
);
