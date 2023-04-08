/*
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
 */


CREATE TABLE IF NOT EXISTS users (
  uuid BIGINT PRIMARY KEY NOT NULL, 
  timezone TEXT NOT NULL DEFAULT 'UTC' CHECK (timezone <> ''), 
  emoji_server BIGINT NOT NULL DEFAULT 0, 
  created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL, 
  CONSTRAINT users_uid_check CHECK (uuid > 0)
);


CREATE TABLE IF NOT EXISTS presence_history (
  id BIGSERIAL PRIMARY KEY NOT NULL, 
  uuid BIGINT NOT NULL, 
  status TEXT NOT NULL, 
  status_before TEXT NOT NULL, 
  changed_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL
);


CREATE 
OR REPLACE FUNCTION limit_presence_history() RETURNS TRIGGER AS $$ BEGIN 
DELETE FROM 
  presence_history 
WHERE 
  uuid = NEW.uuid 
  AND changed_at < (
    SELECT 
      changed_at 
    FROM 
      presence_history 
    WHERE 
      uuid = NEW.uuid 
    ORDER BY 
      changed_at DESC OFFSET 1 
    LIMIT 
      1
  );
RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TABLE IF NOT EXISTS item_history (
  id BIGSERIAL PRIMARY KEY NOT NULL, 
  uuid BIGINT NOT NULL, 
  item_type TEXT NOT NULL, 
  item_value TEXT NOT NULL, 
  changed_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL, 
  CONSTRAINT item_history_item_type_check CHECK (
    item_type IN (
      'avatar', 'discriminator', 'name'
    )
  )
);


CREATE TABLE IF NOT EXISTS avatar_history (
  id BIGSERIAL PRIMARY KEY NOT NULL, 
  uuid BIGINT NOT NULL, 
  format TEXT NOT NULL, -- mime type
  avatar BYTEA NOT NULL, -- image bytes
  changed_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL
);


CREATE 
OR REPLACE FUNCTION insert_avatar_history_item(
  p_user_id bigint, p_format text, p_avatar bytea
) RETURNS void AS $$ BEGIN IF NOT EXISTS (
  WITH last_avatar AS (
    SELECT 
      avatar 
    FROM 
      avatar_history 
    WHERE 
      uuid = p_user_id 
    ORDER BY 
      changed_at DESC 
    LIMIT 
      1
  ) 
  SELECT 
    1 
  FROM 
    last_avatar 
  WHERE 
    avatar = p_avatar
) THEN INSERT INTO avatar_history (uuid, format, avatar) 
VALUES 
  (p_user_id, p_format, p_avatar);
END IF;
END;
$$ LANGUAGE plpgsql;


CREATE 
OR REPLACE FUNCTION limit_avatar_history() RETURNS TRIGGER AS $$ BEGIN 
DELETE FROM 
  avatar_history 
WHERE 
  uuid = NEW.uuid 
  AND changed_at < (
    SELECT 
      changed_at 
    FROM 
      avatar_history 
    WHERE 
      uuid = NEW.uuid 
    ORDER BY 
      changed_at DESC OFFSET 12 
    LIMIT 
      1
  );
RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DO $$ BEGIN IF NOT EXISTS (
  SELECT 
    1 
  FROM 
    pg_trigger 
  WHERE 
    tgname = 'limit_avatar_history'
) THEN CREATE TRIGGER limit_avatar_history 
AFTER 
  INSERT ON avatar_history FOR EACH ROW EXECUTE PROCEDURE limit_avatar_history();
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
  uuid BIGINT NOT NULL, 
  gid BIGINT NOT NULL, 
  word TEXT NOT NULL, -- type of counter
  created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
  CONSTRAINT owo_counting_word_check CHECK (
    word IN ('hunt', 'battle', 'owo')
  )
);


CREATE TABLE IF NOT EXISTS guild_prefixes (
  id BIGSERIAL PRIMARY KEY NOT NULL, 
  gid BIGINT NOT NULL, 
  prefix TEXT NOT NULL, 
  CONSTRAINT guild_prefixes_gid_fk FOREIGN KEY (gid) REFERENCES guilds(gid) ON DELETE CASCADE, 
  CONSTRAINT guild_prefixes_prefix_pk UNIQUE (gid, prefix), 
  CONSTRAINT guild_prefixex_prefix_empty_check CHECK (prefix <> '')
);


CREATE 
OR REPLACE FUNCTION insert_default_prefix() RETURNS TRIGGER AS $$ BEGIN IF NOT EXISTS (
  SELECT 
    1 
  FROM 
    guild_prefixes 
  WHERE 
    gid = NEW.gid
) THEN INSERT INTO guild_prefixes (gid, prefix) 
SELECT 
  NEW.gid, 
  prefix 
FROM 
  (
    SELECT 
      's!' AS prefix 
    UNION ALL 
    SELECT 
      's.'
  ) AS default_prefixes;
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DO $$ BEGIN IF NOT EXISTS (
  SELECT 
    1 
  FROM 
    pg_trigger 
  WHERE 
    tgname = 'insert_default_prefix'
) THEN CREATE TRIGGER insert_default_prefix 
AFTER 
  INSERT ON guilds FOR EACH ROW EXECUTE PROCEDURE insert_default_prefix();
END IF;
END;
$$;


CREATE 
OR REPLACE FUNCTION get_counting_score(p_uuid bigint, p_gid bigint) RETURNS TABLE (
  today bigint, yesterday bigint, this_week bigint, 
  last_week bigint, this_month bigint, 
  last_month bigint, this_year bigint, 
  last_year bigint, all_time bigint
) AS $$ DECLARE all_time_start TIMESTAMP WITH TIME ZONE := '2018-01-01 00:00:00+00';
BEGIN 
SELECT 
  COUNT(*) FILTER (
    WHERE 
      created_at >= now() AT TIME ZONE 'UTC' - INTERVAL '8 hours' 
      AND created_at < now() AT TIME ZONE 'UTC'
  ) AS today_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= now() AT TIME ZONE 'UTC' - INTERVAL '32 hours' 
      AND created_at < now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
  ) AS yesterday_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= date_trunc(
        'week', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) 
      AND created_at < date_trunc(
        'week', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) + INTERVAL '1 week'
  ) AS this_week_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= date_trunc(
        'week', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) - INTERVAL '1 week' 
      AND created_at < date_trunc(
        'week', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      )
  ) AS last_week_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= date_trunc(
        'month', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) 
      AND created_at < date_trunc(
        'month', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) + INTERVAL '1 month'
  ) AS this_month_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= date_trunc(
        'month', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) - INTERVAL '1 month' 
      AND created_at < date_trunc(
        'month', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      )
  ) AS last_month_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= date_trunc(
        'year', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) 
      AND created_at < date_trunc(
        'year', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) + INTERVAL '1 year'
  ) AS this_year_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= date_trunc(
        'year', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      ) - INTERVAL '1 year' 
      AND created_at < date_trunc(
        'year', now() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
      )
  ) AS last_year_count, 
  COUNT(*) FILTER (
    WHERE 
      created_at >= all_time_start 
      AND created_at < now() AT TIME ZONE 'UTC'
  ) AS all_time_count INTO today, 
  yesterday, 
  this_week, 
  last_week, 
  this_month, 
  last_month, 
  this_year, 
  last_year, 
  all_time 
FROM 
  owo_counting;
RETURN QUERY 
SELECT 
  today, 
  yesterday, 
  this_week, 
  last_week, 
  this_month, 
  last_month, 
  this_year, 
  last_year, 
  all_time;
END;
$$ LANGUAGE plpgsql;


CREATE TABLE IF NOT EXISTS bot_pits (
  id BIGSERIAL PRIMARY KEY NOT NULL, 
  uuid BIGINT NOT NULL, -- creator
  appid BIGINT NOT NULL, -- application
  pending BOOLEAN NOT NULL DEFAULT TRUE, -- is the bot pending approval?
  reason TEXT NOT NULL DEFAULT 'Not specified', 
  created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC') NOT NULL, 
  CONSTRAINT bot_pits_uuid_fk FOREIGN KEY (uuid) REFERENCES users(uuid) ON DELETE CASCADE
);
