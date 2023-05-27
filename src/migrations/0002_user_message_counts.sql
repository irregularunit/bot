/*
# Day by Day
------------
> This table is insert aware unlike the monthly tables which are managed by a cron job.
> DateRange: 1 Month

*/
CREATE TABLE IF NOT EXISTS serenity_user_daily_message_counter (
    usnowflake          BIGINT NOT NULL,
    gsnowflake          BIGINT NOT NULL,
    message_type        VARCHAR(6) NOT NULL,
    message_count       BIGINT NOT NULL DEFAULT 0,
    message_timestamp   TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT serenity_user_messages_fkey
        FOREIGN KEY (usnowflake)
        REFERENCES serenity_users(snowflake)
        ON DELETE CASCADE,
    CONSTRAINT serenity_guild_messages_fkey
        FOREIGN KEY (gsnowflake)
        REFERENCES serenity_guilds(snowflake)
        ON DELETE CASCADE,
    CONSTRAINT serenity_message_counting_pkeys
        PRIMARY KEY (usnowflake, gsnowflake, message_type, message_timestamp)
);

/*
# Month by Month
----------------
> Monthly entries are created once a month, from the day by day rows.
> DateRange: 12 Months

*/
CREATE TABLE IF NOT EXISTS serenity_monthly_message_counter (
    usnowflake         BIGINT NOT NULL,
    gsnowflake         BIGINT NOT NULL,
    message_count      BIGINT NOT NULL DEFAULT 0,
    message_type       VARCHAR(6) NOT NULL,
    month_timestamp    TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT serenity_monthly_message_count_fkey
        FOREIGN KEY (usnowflake)
        REFERENCES serenity_users(snowflake)
        ON DELETE CASCADE,
    CONSTRAINT serenity_monthly_message_guild_fkey
        FOREIGN KEY (gsnowflake)
        REFERENCES serenity_guilds(snowflake)
        ON DELETE CASCADE,
    CONSTRAINT serenity_monthly_message_count_pkeys
        PRIMARY KEY (usnowflake, gsnowflake, message_type, month_timestamp)
);

/*
# Total
--------------
> Contains the total message count for each user.
> DateRange: Forever

*/
CREATE TABLE IF NOT EXISTS serenity_total_message_counter (
    usnowflake         BIGINT NOT NULL,
    gsnowflake         BIGINT NOT NULL,
    message_count      BIGINT NOT NULL DEFAULT 0,
    message_type       VARCHAR(6) NOT NULL,
    CONSTRAINT serenity_global_total_message_count_fkey
        FOREIGN KEY (usnowflake)
        REFERENCES serenity_users(snowflake)
        ON DELETE CASCADE,
    CONSTRAINT serenity_global_total_message_guild_fkey
        FOREIGN KEY (gsnowflake)
        REFERENCES serenity_guilds(snowflake)
        ON DELETE CASCADE,
    CONSTRAINT serenity_global_total_message_count_pkeys
        PRIMARY KEY (usnowflake, gsnowflake, message_type)
);


/*
Migration Function to aggregate the message counts from table to table.
*/
CREATE OR REPLACE FUNCTION aggregate_message_counts(aggregation_period TEXT)
RETURNS VOID AS $$
DECLARE
    last_start TIMESTAMP WITH TIME ZONE;
    last_end TIMESTAMP WITH TIME ZONE;
BEGIN
    CASE aggregation_period
        WHEN 'year' THEN
            last_start := date_trunc('year', now() - interval '1 year');
            last_end := date_trunc('year', now());

            INSERT INTO serenity_total_message_counter 
                (usnowflake, gsnowflake, message_count, message_type)
            SELECT 
                usnowflake, gsnowflake, SUM(message_count), message_type
            FROM 
                serenity_monthly_message_counter
            WHERE 
                month_timestamp >= last_start AND month_timestamp < last_end
            GROUP BY 
                usnowflake, gsnowflake, message_type;

            DELETE FROM serenity_monthly_message_counter
            WHERE 
                month_timestamp >= last_start AND month_timestamp < last_end;
    
        WHEN 'month' THEN
            last_start := date_trunc('month', now() - interval '1 month');
            last_end := date_trunc('month', now());

            INSERT INTO serenity_monthly_message_counter 
                (usnowflake, gsnowflake, message_count, message_type, month_timestamp)
            SELECT 
                usnowflake, gsnowflake, SUM(message_count), message_type, last_start
            FROM 
                serenity_user_daily_message_counter
            WHERE 
                message_timestamp >= last_start AND message_timestamp < last_end
            GROUP BY 
                usnowflake, gsnowflake, message_type;

            DELETE FROM serenity_user_daily_message_counter
            WHERE 
                message_timestamp >= last_start AND message_timestamp < last_end;
    
        ELSE
            RAISE EXCEPTION 'Invalid aggregation period. Please choose either "year" or "month".';
    END CASE;
END;
$$ LANGUAGE plpgsql;
