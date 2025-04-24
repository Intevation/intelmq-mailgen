As this component is to be used and released together with others, see
(intelmq-cb-mailgen/NEWS)https://github.com/Intevation/intelmq-mailgen-release).

## 1.3.7

To use the `JSONB` type of IntelMQ's `extra` field directly without conversion, re-create these adjusted functions:

```sql
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

## 1.02 to 1.3.0

 * Changed dependency to use the official Python GnuPG bindings
   and drop support for old pygpgme bindings.
 * Dropped support for Python `v<=3.5.*`
 * Make depending on `pyxarf` module optional.
