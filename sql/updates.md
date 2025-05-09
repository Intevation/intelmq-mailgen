# Update to SQL Database

(most recent on top)

## Adapt to JSONB type of IntelMQ's `extra` field

```sql
SET ROLE eventdb_owner;

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
```

## Add expression index for recipient_group to directives (2019-10)

For each tag that is saved in the `aggregate_identifier` in the directives
table, an index is needed if fast substring searches shall be done.
Note that `intelmq-fody-backend` version>=0.6.4 offers those searches
for the event statistics.

The PostgreSQL extension `pg_trgm` is
packaged in `postgresql-contrib-9.5` for Ubuntu 16.04 LTS.

### forward

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX directives_recipient_group_idx
          ON directives USING gist (
            (json_object(aggregate_identifier) ->> 'recipient_group')
            gist_trgm_ops
          );
```

### backward

```sql
DROP INDEX directives_recipient_group_idx;
DROP EXTENSION pg_trgm CASCADE;
```

## Directive Insertion time-stamp

### forward

```sql
ALTER TABLE directives ADD COLUMN inserted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE directives ALTER COLUMN inserted_at SET DEFAULT CURRENT_TIMESTAMP;
UPDATE directives
   SET inserted_at = (SELECT "time.observation" FROM events
                      WHERE id = events_id)
 WHERE inserted_at IS NULL;
ALTER TABLE directives ALTER COLUMN inserted_at SET NOT NULL;
```

### backward

```sql
ALTER TABLE DROP COLUMN inserted_at;
```

## Adapt directives_grouping_idx to actually used grouping columns

### forward

```sql
DROP INDEX directives_grouping_idx;
CREATE INDEX directives_grouping_idx
          ON directives (recipient_address, template_name,
                         notification_format, event_data_format,
                         aggregate_identifier);
```

## backward

```sql
DROP INDEX directives_grouping_idx;
CREATE INDEX directives_grouping_idx
          ON directives (medium, recipient_address, template_name,
                         notification_format, event_data_format,
                         aggregate_identifier, endpoint);
```

## New notification handling

See git history


## adding ticket_number #28

### forward

```sql
CREATE TABLE ticket_day (
    initialized_for_day DATE
);
GRANT SELECT, UPDATE ON ticket_day TO eventdb_send_notifications;

ALTER TABLE notifications ALTER COLUMN intelmq_ticket TYPE VARCHAR(18);

DROP SEQUENCE intelmq_ticket_seq;
CREATE SEQUENCE intelmq_ticket_seq MINVALUE 10000001;
ALTER SEQUENCE intelmq_ticket_seq OWNER TO eventdb_send_notifications;
```

### backwards

```sql
DROP SEQUENCE intelmq_ticket_seq;
CREATE SEQUENCE intelmq_ticket_seq;
GRANT USAGE ON intelmq_ticket_seq TO eventdb_send_notifications;

DROP TABLE ticket_day;

-- will only work if all old entries can still be converted
ALTER TABLE notifications ALTER COLUMN intelmq_ticket TYPE BIGINT;
```
