-- Initialize the notifications part of the event DB.
--
-- The notifications part keeps track of which emails are to be sent and
-- which have already been sent in the notifications table. There's also
-- a trigger on the events table that automatically extracts the
-- notification information added to events by the certbund_contact bot
-- and inserts it into notifications.

BEGIN;


CREATE ROLE eventdb_owner
    NOLOGIN NOSUPERUSER NOINHERIT NOCREATEDB CREATEROLE;
CREATE ROLE eventdb_insert
    NOLOGIN NOSUPERUSER NOINHERIT NOCREATEDB CREATEROLE;
CREATE ROLE eventdb_send_notifications
    NOLOGIN NOSUPERUSER NOINHERIT NOCREATEDB CREATEROLE;

ALTER DATABASE :"DBNAME" OWNER TO eventdb_owner;

ALTER TABLE events OWNER TO eventdb_owner;

-- must be superuser to create type
CREATE TYPE ip_endpoint AS ENUM ('source', 'destination');

CREATE SEQUENCE intelmq_ticket_seq MINVALUE 10000001;
ALTER SEQUENCE intelmq_ticket_seq OWNER TO eventdb_send_notifications;

SET ROLE eventdb_owner;

GRANT INSERT ON events TO eventdb_insert;
GRANT USAGE ON events_id_seq TO eventdb_insert;
GRANT SELECT ON events TO eventdb_send_notifications;

-- a single row table to save which day we currently use for intelmq_ticket
CREATE TABLE ticket_day (
        initialized_for_day DATE
);
INSERT INTO ticket_day (initialized_for_day) VALUES('20160101');
GRANT SELECT, UPDATE ON ticket_day TO eventdb_send_notifications;


CREATE TABLE sent (
    id BIGSERIAL UNIQUE PRIMARY KEY,
    intelmq_ticket VARCHAR(18) UNIQUE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE
);


GRANT SELECT, INSERT ON sent TO eventdb_send_notifications;
GRANT USAGE ON sent_id_seq TO eventdb_send_notifications;


CREATE TABLE directives (
    id BIGSERIAL UNIQUE PRIMARY KEY,
    events_id BIGINT NOT NULL,
    sent_id BIGINT,

    medium VARCHAR(100) NOT NULL,
    recipient_address VARCHAR(100) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    notification_format VARCHAR(100) NOT NULL,
    event_data_format VARCHAR(100) NOT NULL,
    aggregate_identifier TEXT[][],
    notification_interval INTERVAL NOT NULL,
    endpoint ip_endpoint NOT NULL,

    inserted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (events_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (sent_id) REFERENCES sent(id) ON DELETE CASCADE
);


CREATE INDEX directives_grouping_inserted_at_idx
          ON directives (recipient_address, template_name,
                         notification_format, event_data_format,
                         aggregate_identifier, inserted_at);
CREATE INDEX directives_events_id_idx
          ON directives (events_id);
CREATE INDEX directives_sent_id_idx
          ON directives (sent_id);

-- Use https://www.postgresql.org/docs/9.5/pgtrgm.html to allow for
-- fast ILIKE search in tags saved in the aggregate_identifier.
-- If additional tags are entered there, additional indixes may be advisable.
CREATE EXTENSION pg_trgm;
CREATE INDEX directives_recipient_group_idx
          ON directives USING gist (
            (json_object(aggregate_identifier) ->> 'recipient_group')
            gist_trgm_ops
          );

GRANT SELECT, UPDATE ON directives TO eventdb_send_notifications;


-- Converts a JSON object used as aggregate identifier to a
-- 2-dimensional TEXT array usable as a value in the database for
-- grouping. Doing this properly is a bit tricky. Requirements:
--
--  1. the type must allow comparison because we need to be able to
--     GROUP BY the aggregate_identifier column
--
--  2. The value must be chosen to preserve the equivalence relation on
--     the abstract aggregate identifier, meaning
--
--      (a) Equal aggregate identifiers have to be mapped to the equal
--          values
--
--      (b) equal values must imply equal aggregate identifiers
--
-- Requirement 1 rules out using JSON directly because it doesn't
-- support comparison. We cannot use JSONB either because that type is
-- not available in PostgreSQL 9.3 (JSONB requires at least 9.4). Simply
-- converting the JSON object to TEXT is not an option either since, for
-- instance, the order of the keys would not be predictable.
--
-- Requirement 2 means we need to be careful when choosing the
-- representation. An easy solution would be to iterate over the JSON
-- object with the json_each or json_each_text functions. Neither is
-- really good. json_each returns the values as JSON objects in which
-- case the conversion to TEXT will not preserve equality in the case of
-- Strings because escape sequences will not be normalized.
-- json_each_text returns the values as text which means that numbers
-- and strings cannot be distinguished reliably (123 and "123" would be
-- considered equal).
--
-- Given that we might switch to PostgreSQL 9.5 which comes with Ubuntu
-- 16.4 LTS we go with json_each_text because in most cases the values
-- will have come from IntelMQ events where the values have been
-- validated and e.g. ASNs will always be numbers.
CREATE OR REPLACE FUNCTION json_object_as_text_array(obj JSONB)
RETURNS TEXT[][]
AS $$
DECLARE
    arr TEXT[][] = '{}'::TEXT[][];
    k TEXT;
    v TEXT;
BEGIN
    FOR k, v IN
        SELECT * FROM jsonb_each_text(obj) ORDER BY key
    LOOP
        arr := arr || ARRAY[ARRAY[k, v]];
    END LOOP;
    RETURN arr;
END
$$ LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION insert_directive(
    event_id BIGINT,
    directive JSONB,
    endpoint ip_endpoint
) RETURNS VOID
AS $$
DECLARE
    medium TEXT := directive ->> 'medium';
    recipient_address TEXT := directive ->> 'recipient_address';
    template_name TEXT := directive ->> 'template_name';
    notification_format TEXT := directive ->> 'notification_format';
    event_data_format TEXT := directive ->> 'event_data_format';
    aggregate_identifier TEXT[][]
        := json_object_as_text_array(directive -> 'aggregate_identifier');
    notification_interval interval
        := coalesce(((directive ->> 'notification_interval') :: INT)
                    * interval '1 second',
                    interval '0 second');
BEGIN
    IF medium IS NOT NULL
       AND recipient_address IS NOT NULL
       AND template_name IS NOT NULL
       AND notification_format IS NOT NULL
       AND event_data_format IS NOT NULL
       AND notification_interval IS NOT NULL
       AND notification_interval != interval '-1 second'
    THEN
        INSERT INTO directives (events_id,
                                medium,
                                recipient_address,
                                template_name,
                                notification_format,
                                event_data_format,
                                aggregate_identifier,
                                notification_interval,
                                endpoint)
        VALUES (event_id,
                medium,
                recipient_address,
                template_name,
                notification_format,
                event_data_format,
                aggregate_identifier,
                notification_interval,
                endpoint);
    END IF;
END
$$ LANGUAGE plpgsql VOLATILE;


CREATE OR REPLACE FUNCTION directives_from_extra(
    event_id BIGINT,
    extra JSONB
) RETURNS VOID
AS $$
DECLARE
    json_directives JSONB := extra -> 'certbund' -> 'source_directives';
    directive JSONB;
BEGIN
    IF json_directives IS NOT NULL THEN
        FOR directive
         IN SELECT * FROM jsonb_array_elements(json_directives) LOOP
            PERFORM insert_directive(event_id, directive, 'source');
        END LOOP;
    END IF;
END
$$ LANGUAGE plpgsql VOLATILE;


CREATE OR REPLACE FUNCTION events_insert_directives_for_row()
RETURNS TRIGGER
AS $$
BEGIN
    PERFORM directives_from_extra(NEW.id, NEW.extra);
    RETURN NEW;
END
$$ LANGUAGE plpgsql VOLATILE EXTERNAL SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION events_insert_directives_for_row()
TO eventdb_insert;


CREATE TRIGGER events_insert_directive_trigger
AFTER INSERT ON events
FOR EACH ROW
EXECUTE PROCEDURE events_insert_directives_for_row();


COMMIT;
