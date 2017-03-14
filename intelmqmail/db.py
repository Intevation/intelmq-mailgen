"""Access to the event/notification database."""

import string
import json
import logging

import psycopg2
import psycopg2.errorcodes


log = logging.getLogger(__name__)


def open_db_connection(config, connection_factory=None):
    """Opens a psycopg2 database connection.

    Does not set autocommit, so using code must take
    care about transaction handling itself.
    """
    params = config['database']['event']
    return psycopg2.connect(database=params['name'],
                            user=params['username'],
                            password=params['password'],
                            host=params['host'],
                            port=params['port'],
                            # sslmode=params['sslmode'],
                            connection_factory=connection_factory)


PENDING_DIRECTIVES_QUERY = """\
   SELECT d.recipient_address as recipient_address,
          d.template_name as template_name,
          d.event_data_format as event_data_format,
          d.aggregate_identifier as aggregate_identifier,
          array_agg(d.events_id) as event_ids,
          array_agg(d.id) as directive_ids
     FROM (SELECT id, events_id, recipient_address, template_name,
                  event_data_format, notification_interval,
                  aggregate_identifier
             FROM directives
            WHERE sent_id IS NULL
              AND medium = 'email'
              AND endpoint = 'source'
            FOR UPDATE NOWAIT) d
 GROUP BY d.recipient_address, d.template_name, d.event_data_format,
          d.aggregate_identifier
   HAVING coalesce((SELECT max(s.sent_at)
                      FROM directives d2
                      JOIN sent s ON d2.sent_id = s.id
                     WHERE d2.recipient_address = d.recipient_address
                       AND d2.template_name = d.template_name
                       AND d2.event_data_format = d.event_data_format
                       AND d2.aggregate_identifier = d.aggregate_identifier)
                   + max(d.notification_interval)
                   < CURRENT_TIMESTAMP,
                   TRUE);
"""

def get_pending_notifications(cur):
    """Retrieve all pending directives from the database.
    Directives are pending if the notification they describe hasn't been
    sent yet and the last time a similar notification has been sent was
    long enough ago that the notification interval has been exceeded.
    The directives are grouped according to the aggregation identifier.

    :returns: list of aggreated directives
    :rtype: list
    """
    try:
        cur.execute(PENDING_DIRECTIVES_QUERY)
    except psycopg2.OperationalError as e:
        if e.pgcode == psycopg2.errorcodes.LOCK_NOT_AVAILABLE:
            log.info("Could not get db lock for pending notifications. "
                     "Probably another instance of myself is running.")
            return None
        else:
            raise

    return cur.fetchall()


# characters allowed in identifiers in escape_sql_identifier. There are
# just the characters that are used in IntelMQ for identifiers in the
# events table.
sql_identifier_charset = set(string.ascii_letters + string.digits + "_.")


def escape_sql_identifier(ident):
    if set(ident) - sql_identifier_charset:
        raise ValueError("Event column identifier %r contains invalid"
                         " characters (%r)"
                         % (ident, set(ident) - sql_identifier_charset))
    return '"' + ident + '"'


def load_events(cur, event_ids, columns=None):
    """Return events for the ids with all or a subset of available columns.

    Use the columns parameter to specify which columns to return.

    :param cur: database connection
    :param event_ids: list of events ids
    :param columns: list of column names, defaults to all if 'None' is given.
    returns: corresponding events as a list of dictionaries
    """
    if columns is not None:
        sql_columns = ", ".join(escape_sql_identifier(col) for col in columns)
    else:
        sql_columns = "*"
    cur.execute("SELECT {} FROM events WHERE id = ANY (%s)".format(sql_columns),
                (event_ids,))

    return cur.fetchall()


def new_ticket_number(cur):
    """Draw a new unique ticket number.

    Check the database and reset the ticket counter if
    our day is past the last initialisation day.
    Raise RuntimeError if last initialisation is in the future, because
    we may potentially reuse ticket numbers if we get to this day.

    :returns: a unique ticket-number string in format YYYYMMDD-XXXXXXXX
    :rtype: string
    """
    sqlQuery = """SELECT to_char(now(), 'YYYYMMDD') AS date,
                         (SELECT to_char(initialized_for_day, 'YYYYMMDD')
                              FROM ticket_day) AS init_date,
                         nextval('intelmq_ticket_seq');"""
    cur.execute(sqlQuery)
    result = cur.fetchall()
    #log.debug(result)

    date_str = result[0]["date"]
    if date_str != result[0]["init_date"]:
        if date_str < result[0]["init_date"]:
            raise RuntimeError(
                    "initialized_for_day='{}' is in the future from now(). "
                    "Stopping to avoid reusing "
                    "ticket numbers".format(result[0]["init_date"]))

        log.debug("We have a new day, reseting the ticket generator.")
        cur.execute("ALTER SEQUENCE intelmq_ticket_seq RESTART;")
        cur.execute("UPDATE ticket_day SET initialized_for_day=%s;",
                    (date_str,));

        cur.execute(sqlQuery)
        result = cur.fetchall()
        log.debug(result)

    ticket = _format_ticket(date_str, result[0]["nextval"])
    log.debug('New ticket number "{}".'.format(ticket,))

    return ticket

def _format_ticket(date_str, sequence_number: int) -> str:
    # num_str from integer: fill with 0s and cut out 8 chars from the right
    num_str = "{:08d}".format(sequence_number)[-8:]
    ticket = "{:s}-{:s}".format(date_str, num_str)

    return ticket


def last_ticket_number(cur) -> str:
    """Return a ticket number that has recently been drawn.

    Because of race conditions, there might by other tickets numbers already
    drawn or the emails may not be send out yet.
    """
    sql_query = """SELECT
                     (SELECT to_char(initialized_for_day, 'YYYYMMDD')
                        FROM ticket_day) AS day,
                     last_value FROM intelmq_ticket_seq;"""

    cur.execute(sql_query)
    result = cur.fetchone()

    return _format_ticket(result["day"], result["last_value"])


def mark_as_sent(cur, directive_ids, ticket):
    "Mark notifactions with given ids as sent and set the ticket number."
    log.debug("Marking directive ids {} as sent.".format(directive_ids))
    cur.execute("""\
                  WITH sent_row AS (INSERT INTO sent (intelmq_ticket, sent_at)
                                         VALUES (%s, now())
                                      RETURNING id)
                UPDATE directives
                   SET sent_id = (SELECT id FROM sent_row)
                 WHERE id = ANY (%s);""",
                (ticket, directive_ids,))
