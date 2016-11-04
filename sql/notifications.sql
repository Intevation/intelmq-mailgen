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

CREATE SEQUENCE intelmq_ticket_seq MINVALUE 10000001;
ALTER SEQUENCE intelmq_ticket_seq OWNER TO eventdb_send_notifications;

SET ROLE eventdb_owner;

GRANT INSERT ON events TO eventdb_insert;
GRANT USAGE ON events_id_seq TO eventdb_insert;
GRANT SELECT ON events TO eventdb_send_notifications;


CREATE TYPE ip_endpoint AS ENUM ('source', 'destination');


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
    event_data_format VARCHAR(100) NOT NULL,
    aggregate_identifier TEXT,
    notification_interval INTERVAL NOT NULL,
    endpoint ip_endpoint NOT NULL,

    FOREIGN KEY (events_id) REFERENCES events(id),
    FOREIGN KEY (sent_id) REFERENCES sent(id)
);


CREATE INDEX directives_grouping_idx
          ON directives (medium, recipient_address, template_name,
                         event_data_format, aggregate_identifier, endpoint);
CREATE INDEX directives_events_id_idx
          ON directives (events_id);
CREATE INDEX directives_sent_id_idx
          ON directives (sent_id);

GRANT SELECT, UPDATE ON directives TO eventdb_send_notifications;


CREATE OR REPLACE FUNCTION insert_directive(
    event_id BIGINT,
    directive JSON,
    endpoint ip_endpoint
) RETURNS VOID
AS $$
DECLARE
    medium TEXT := directive ->> 'medium';
    recipient_address TEXT := directive ->> 'recipient_address';
    template_name TEXT := directive ->> 'template_name';
    event_data_format TEXT := directive ->> 'event_data_format';
    notification_interval interval
        := coalesce(((directive ->> 'notification_interval') :: INT)
                    * interval '1 second',
                    interval '0 second');
BEGIN
    IF medium IS NOT NULL
       AND recipient_address IS NOT NULL
       AND template_name IS NOT NULL
       AND event_data_format IS NOT NULL
       AND notification_interval IS NOT NULL    
       AND notification_interval != interval '-1 second'
    THEN
        INSERT INTO directives (events_id,
                                medium,
                                recipient_address,
                                template_name,
                                event_data_format,
                                notification_interval,
                                endpoint)
        VALUES (event_id,
                medium,
                recipient_address,
                template_name,
                event_data_format,
                notification_interval,
                endpoint);
    END IF;
END
$$ LANGUAGE plpgsql VOLATILE;


CREATE OR REPLACE FUNCTION directives_from_extra(
    event_id BIGINT,
    extra JSON
) RETURNS VOID
AS $$
DECLARE
    json_directives JSON := extra -> 'certbund' -> 'source_directives';
    directive JSON;
BEGIN
    IF json_directives IS NOT NULL THEN
        FOR directive
         IN SELECT * FROM json_array_elements(json_directives) LOOP
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
