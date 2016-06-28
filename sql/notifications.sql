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

SET ROLE eventdb_owner;

GRANT INSERT ON events TO eventdb_insert;
GRANT USAGE ON events_id_seq TO eventdb_insert;
GRANT SELECT ON events TO eventdb_send_notifications;


CREATE TYPE ip_endpoint AS ENUM ('source', 'destination');


CREATE SEQUENCE intelmq_ticket_seq;
GRANT USAGE ON intelmq_ticket_seq TO eventdb_send_notifications;


CREATE TABLE notifications (
    id BIGSERIAL UNIQUE PRIMARY KEY,
    intelmq_ticket BIGINT,
    events_id BIGINT NOT NULL,
    email VARCHAR(100) NOT NULL,
    format VARCHAR(100) NOT NULL,
    notification_interval INTERVAL NOT NULL,
    endpoint ip_endpoint NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,

    -- Event data to help select the template
    feed_name VARCHAR(2000) NOT NULL,
    classification_taxonomy VARCHAR(100) NOT NULL,
    classification_type VARCHAR(100) NOT NULL,
    classification_identifier VARCHAR(100),
    malware_name VARCHAR(100),
    contact_sector VARCHAR(100),
    contact_organisation VARCHAR(100),
    contact_name VARCHAR(100),

    FOREIGN KEY (events_id) REFERENCES events(id)
);

CREATE INDEX notifications_grouping_idx
          ON notifications (email, template, format);
CREATE INDEX notifications_intelmq_ticket_idx
          ON notifications (intelmq_ticket);

GRANT SELECT, UPDATE ON notifications TO eventdb_send_notifications;

/*
 Template
*/
CREATE TABLE template (
    id BIGSERIAL UNIQUE PRIMARY KEY,

    -- feed name
    feed_name VARCHAR(2000),

    -- Taxonomy
    classification_taxonomy VARCHAR(100), -- currently not used

    -- The classification type for which this template can be used.
    classification_type VARCHAR(100),

    -- Classification identifier
    classification_identifier VARCHAR(100), -- currently not used

    -- Name of the malware or similar
    malware_name VARCHAR(100), -- currently not used

    -- Contact sector
    contact_sector VARCHAR(100),

    -- Contact organisation
    contact_organisation VARCHAR(100),

    -- Contact
    contact_name VARCHAR(100),

    -- Path of the template
    path VARCHAR(200) NOT NULL,
);

CREATE OR REPLACE FUNCTION insert_notification(
    event_id BIGINT,
    notification JSON,
    notification_endpoint ip_endpoint,
    classification_type VARCHAR(100),
    feed_name VARCHAR(2000)
) RETURNS VOID
AS $$
DECLARE
    email TEXT := notification ->> 'email';
    format TEXT := notification ->> 'format';
    template TEXT := notification ->> 'template_path';
    notification_interval interval
        := ((notification ->> 'ttl') :: INT) * interval '1 second';
BEGIN
    IF email IS NOT NULL
       AND format IS NOT NULL
       AND template IS NOT NULL
       AND notification_interval IS NOT NULL
    THEN
        INSERT INTO notifications (events_id,
                                   email,
                                   format,
                                   template,
                                   classification_type,
                                   feed_name,
                                   notification_interval,
                                   endpoint)
        VALUES (event_id,
                email,
                format,
                template,
                classification_type,
                feed_name,
                notification_interval,
                notification_endpoint);
    END IF;
END
$$ LANGUAGE plpgsql VOLATILE;


CREATE OR REPLACE FUNCTION notifications_from_extra(
    event_id BIGINT,
    extra JSON,
    classification_type VARCHAR(100),
    feed_name VARCHAR(2000)
) RETURNS VOID
AS $$
DECLARE
    json_notifications JSON := extra -> 'certbund' -> 'notify_source';
    notification JSON;
BEGIN
    IF json_notifications IS NOT NULL THEN
        FOR notification
         IN SELECT * FROM json_array_elements(json_notifications) LOOP
            PERFORM insert_notification(event_id,
                                        notification,
                                        'source',
	                                    classification_type,
	                                    feed_name);
        END LOOP;
    END IF;
END
$$ LANGUAGE plpgsql VOLATILE;


CREATE OR REPLACE FUNCTION events_insert_notifications_for_row()
RETURNS TRIGGER
AS $$
BEGIN
    PERFORM notifications_from_extra(NEW.id,
                                     NEW.extra,
                                     NEW."classification.type",
                                     NEW."feed.name");
    RETURN NEW;
END
$$ LANGUAGE plpgsql VOLATILE EXTERNAL SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION events_insert_notifications_for_row()
TO eventdb_insert;


CREATE TRIGGER events_insert_notification_trigger
AFTER INSERT ON events
FOR EACH ROW
EXECUTE PROCEDURE events_insert_notifications_for_row();


COMMIT;
