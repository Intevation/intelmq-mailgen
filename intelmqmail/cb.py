#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command line tool to send notfications for intelmq events.


Copyright (C) 2016 by Bundesamt für Sicherheit in der Informationstechnik
Software engineering by Intevation GmbH

This program is Free Software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Authors:
    Bernhard Herzog <bernhard.herzog@intevation.de>
    Roland Geider <roland.geider@intevation.de>
    Bernhard E. Reiter <bernhard@intevation.de>

    and others.

Based upon intelmqcli
https://github.com/certat/intelmq/blob/master/intelmq/bin/intelmqcli.py


Requires at least Python 3.2 because of DictWriter.writeheader()
"""

import smtplib
import argparse
import json
import locale
import logging
import os
import sys
import io
import csv
import string
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

import gpgme  # developed for pygpgme 0.3
import psycopg2
from psycopg2.extras import RealDictConnection

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s - %(message)s')
log = logging.getLogger('intelmq-mailgen')
log.setLevel(logging.INFO)  # defaults to WARNING
#log.setLevel(logging.DEBUG)  # defaults to WARNING

if locale.getpreferredencoding() != 'UTF-8':
    log.critical(
        'The preferred encoding of your locale setting is not UTF-8'
        ' but "{}". Exiting.'.format(locale.getpreferredencoding()))
    exit(1)

APPNAME = "intelmqcbmail"
DESCRIPTION = """
"""

EPILOG = """
Searches for all unprocessed notifications and sends them.
"""

USAGE = """
    {appname}
    {appname} --all
""".format(appname=APPNAME)


def read_configuration():
    """Read configuration from user and system settings.
    The return value is a dictionary containing the merged settings read
    from the configuration files.
    """
    # Construct a single configuration dictionary with the contents of
    # the different conf files
    home = os.path.expanduser("~")  # needed for OSX
    user_conf_file = os.path.expanduser(home +
                                        '/.intelmq/intelmq-mailgen.conf')
    sys_conf_file = os.path.expanduser('/etc/intelmq/intelmq-mailgen.conf')
    if os.path.isfile(user_conf_file):
        with open(user_conf_file) \
             as conf_handle:
            user_config = json.load(conf_handle)
    else:
        user_config = dict()
    if os.path.isfile(sys_conf_file):
        with open(sys_conf_file) as conf_handle:
            system_config = json.load(conf_handle)
    else:
        system_config = dict()

    combined = system_config.copy()
    for key, value in user_config.items():
        if isinstance(combined.get(key), dict):
            combined[key].update(value)
        else:
            combined[key] = value

    if not combined:
        raise OSError("No configuration found.")

    return combined


def open_db_connection(config):
    params = config['database']['event']
    return psycopg2.connect(database=params['name'],
                            user=params['username'],
                            password=params['password'],
                            host=params['host'],
                            port=params['port'],
                            # sslmode=params['sslmode'],
                            connection_factory=RealDictConnection)


def full_template_filename(template_dir, template_name):
    """Return the full absolute file name of a template.

    The template_name parameter is interpreted relative to template_dir
    and must refer to a file under that directory. If the resulting file
    name would name a file outside of template_dir, a ValueError
    exception is raised. This check is done to guard against malicious
    template names.
    """
    # make sure absbase ends with "/" so that the check whether the
    # resulting template file name is located under template_dir
    # actually works. os.path.abspath will remove any trailing slashes
    # from its parameter so we can simply append a single one.
    absbase = os.path.abspath(template_dir) + os.path.sep
    absfilename = os.path.abspath(os.path.join(template_dir, template_name))
    if not absfilename.startswith(absbase):
        raise ValueError("Invalid template name %r! Full template filename"
                         " would be outside of the template base directory %r."
                         % (template_name, template_dir))
    return absfilename


def read_template(template_dir, template_name):
    """Read the email template indicated by template_dir and template_name.

    The name of the template file is determined with full_template_filename.

    File Format:

      - The first non-empty line of the file is assumed to be the
        template string for the subject line of the email.

      - The rest of the lines are the email body. Leading and trailing
        white space is removed from the body and a newline added at the
        end. This allows e.g. an empty line in the template between the
        subject line and the body.

        The resulting string is used as template string in a Python
        Template object, thus allowing some simple substitutions. See
        the different formatter implementations for the substitions they
        support.

    The return value is a pair of the subject and the body where both
    are an instances of string.Template.
    """
    with open(full_template_filename(template_dir, template_name)) as infile:
        subject = None
        while not subject:
            subject = infile.readline().strip()
        subject = string.Template(subject)
        body = string.Template(infile.read().strip() + "\n")
        return subject, body

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
    returns: corresponding events as a list of dictionaries including an
             extra array "notification_ids" holding the n_ids of the event
    """
    if columns is not None:
        sql_columns = ", ".join(escape_sql_identifier(col) for col in columns)
    else:
        sql_columns = "*"
    cur.execute("SELECT {},"
                "       ARRAY(SELECT id from notifications"
                "             WHERE events_id = events.id) as notification_ids"
                "  FROM events WHERE id = ANY (%s)".format(sql_columns),
                (event_ids,))

    return cur.fetchall()


def create_mail(sender, recipient, subject, body, attachments):
    """Create an email either as single or multi-part with attachments."""
    if len(attachments) == 0:
        msg = MIMEText(body, _charset="utf-8")
    else:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, _charset="utf-8"))

        for filename, contents, maintype, subtype in attachments:
            part = MIMEBase(maintype, subtype, filename=filename)
            part.set_payload(contents)
            msg.attach(part)

    msg.add_header("From", sender)
    msg.add_header("To", recipient)
    msg.add_header("Subject", subject)
    msg.add_header("Date", formatdate(timeval=None, localtime=True))

    return msg


def clearsign(gpgme_ctx, text):
    plaintext = io.BytesIO(text.encode())
    signature = io.BytesIO()

    try:
        sigs = gpgme_ctx.sign(plaintext, signature, gpgme.SIG_MODE_CLEAR)
    except:
        log.error("OpenPGP signing failed!")
        raise

    signature.seek(0)
    return(signature.read().decode())


def format_as_csv(columns, events, header):
    """ Creates an events.csv
    :columns: a list of columns
    :events: an array containing the events as dicts
    :header: Mapping of columns to column titles for the header line
    """
    contents = io.StringIO()
    writer = csv.DictWriter(contents, columns, delimiter="|")
    writer.writerow(header)

    for event in events:
        if event.get('time.source'):
            event['time.source'] = event['time.source'].replace(tzinfo=None)
        writer.writerow(event)

    return ("events.csv", contents.getvalue(), "text", "csv")


def mail_format_as_csv(cur, agg_notification, config, gpgme_ctx, format_spec):
    """Creates emails with csv attachment for given columns.

    Groups the events by 'source.asn' and creates an email for each.
    TODO: Assumes that all events have such a value.

    :returns: list of tuples (email object, list of notification ids, ticket)
    :rtype: list
    """
    attachments = []

    events = load_events(cur, agg_notification["event_ids"],
                         format_spec.event_table_columns())


    # grouping the events by asn, so we have a list of events for each
    events_per_asn = {}
    asnk = "source.asn"
    for event in events:
        if not asnk in event or not event[asnk]:
            raise RuntimeError(
                    "Missing '{%s}' in event {}".format(asnk, event))
        asn = event[asnk]
        events_per_asn.setdefault(asn, []).append(event)

    email_tuples = []
    log.debug("Found {} ASN(s) in batch.".format(len(events_per_asn)))
    for asn in events_per_asn:
        events_as_csv = format_as_csv(format_spec.csv_column_keys(),
                                      [format_spec.csv_row_from_event(event)
                                       for event in events_per_asn[asn]],
                                      format_spec.column_titles())[1]

        n_ids = [] #ids of the affected notifications
        for event in events_per_asn[asn]:
            n_ids.extend(event["notification_ids"])

        ticket = new_ticket_number(cur)

        subject_template, body_template = read_template(
                                            config["template_dir"],
                                            agg_notification["template"])

        subject = subject_template.substitute(asn=asn, ticket_number=ticket)
        body = body_template.substitute(events_as_csv=events_as_csv,
                                        asn=asn, ticket_number=ticket)

        if gpgme_ctx:
            body = clearsign(gpgme_ctx, body)

        mail = create_mail(sender=config["sender"],
                           recipient=agg_notification["email"],
                           subject=subject, body=body,
                           attachments=attachments)

        email_tuples.append((mail, n_ids, ticket))
    return email_tuples


def mail_format_feed_specific_as_csv(cur, agg_notification, config, gpgme_ctx):
    """Creates emails with csv attachment based on feed-name.

    This function assumes that notification["feed_name"] is actually one
    of the feed names used as key in feed_specific_formats.

    :returns: list of tuples (email object, list of ids, ticket)
    :rtype: list
    """
    feed_name = agg_notification["feed_name"]
    format_spec = feed_specific_formats.get(feed_name)
    if format_spec is None:
        # TODO
        raise RuntimeError
    agg_notification["template"] = "template-" + feed_name + ".txt"

    return mail_format_as_csv(cur, agg_notification,
                              config, gpgme_ctx, format_spec)


class FeedSpecificFormat:

    """Describe a feed-specific CSV format.
    """

    def __init__(self, feed_name, columns):
        """Initialize the format specification.
        The columns parameter should be a list of Column instances."""
        self.feed_name = feed_name
        self.columns = columns

    def column_titles(self):
        """Return a dictionary with the column titles for use a CSV header."""
        return dict((col.csv_column_key, col.title) for col in self.columns)

    def event_table_columns(self):
        """Return a list with the columns to retrieve from the event table.
        """
        return list(set(col.event_table_column for col in self.columns))

    def csv_column_keys(self):
        """Return a list with the keys used for the CSV rows.
        The list is to be used as the field names parameter for the
        csv.DictWriter class and matches the dictionaries returned by the
        csv_row_from_event method.
        """
        return [col.csv_column_key for col in self.columns]

    def csv_row_from_event(self, event):
        """Return the csv row for one given event."""
        return dict((col.csv_column_key, col.csv_value_from_event(event))
                    for col in self.columns)



class Column:

    """Specifies a single column for CSV output.

    This base class only provides a title for the column.

    Derived classes should implement the following attributes and methods:

    :title: the column title
    :event_table_column: the column of the event table to retrieve
    :csv_column_key: a key to use for the CSV row dictionary.
        All columns of a single format must have different
        csv_column_key values.
    :csv_value_from_event(event): Return the value of the column for the
        given event. The event parameter is a dictionary that has at
        least a value for the event_table_column.
    """

    def __init__(self, title):
        self.title = title


class IntelMQColumn(Column):

    """CSV Column filled directly from an IntelMQ field."""

    def __init__(self, title, field_name):
        super(IntelMQColumn, self).__init__(title)
        self.field_name = field_name

    @property
    def event_table_column(self):
        return self.field_name

    @property
    def csv_column_key(self):
        return self.field_name

    def csv_value_from_event(self, event):
        return event[self.field_name]


class ExtraColumn(Column):

    """CSV Column filled with a value taken from the IntelMQ extra field.

    The extra_key parameter of the constructor gives the name key to
    look up in the JSON dictionary contained in the extra field.
    """

    def __init__(self, title, extra_key):
        super(ExtraColumn, self).__init__(title)
        self.extra_key = extra_key

    @property
    def event_table_column(self):
        return "extra"

    @property
    def csv_column_key(self):
        return "extra:" + self.extra_key

    def csv_value_from_event(self, event):
        value = event[self.event_table_column]
        if isinstance(value, str):
            # With psycopg 2.4.5 values of type JSON in the database are
            # returned as strings. In newer psycopg versions they are
            # converted automatically, so we may not have to convert the
            # value.
            # FIXME: This aspect (not having to convert with newer psycopg
            # versions) has not been tested.
            value = json.loads(value)
        return value.get(self.extra_key)



# convenience functions for building the format datastructures in a more
# declarative way.

def build_feed_specific_formats(formats):
    """Return a dictionary mapping format names to format specifications.
    The parameter is a list of (formatname, columns) pairs, where
    formatname is the name of the format as a string and columns is a
    list of column specifications. The formatname values are used as the
    keys in the dictionary and both formatname and columns are passed to
    build_feed_specific_format to create the corresponding format
    specification.
    """
    return dict((name, build_feed_specific_format(name, columns))
                for name, columns in formats)

def build_feed_specific_format(feed_name, columns):
    """Build a FeedSpecificFormat instance for feed_name.
    The columns parameter should be a list of column specifications
    which are passed to build_feed_specific_column to create the list of
    columns for the FeedSpecificFormat instance.
    """
    return FeedSpecificFormat(feed_name,
                              [build_feed_specific_column(col)
                               for col in columns])

def build_feed_specific_column(col):
    """Return a Column instance built from a column specification.
    A column specification may either be a tuple of the form
    (intelmq_field, column_title) in which case an IntelMQColumn is
    created from these parameters or an instance of Column which is
    returned as is.
    """
    if isinstance(col, tuple):
        intelmq_field, column_title = col
        return IntelMQColumn(column_title, intelmq_field)
    else:
        return col


# Specifications for the feed_specific formats
feed_specific_formats = build_feed_specific_formats([

    ("generic_malware", [
        # this is used for the following feeds:
        #   "Botnet-Drone-Hadoop", "Sinkhole-HTTP-Drone",
        #   "Microsoft-Sinkhole"
        # These names are all mapped to "generic_malware" in
        # get_pending_notifications before the grouping
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ("classification.identifier", "Malware"),
        ("source.port", "Source Port"),
        ("destination.ip", "Target IP"),
        ("destination.port", "Target Port"),
        ("protocol.transport", "Protocol"),
        ("destination.fqdn", "Target Hostname"),
        ]),
    ("DNS-open-resolvers", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Min. amplification", "min_amplification"),
        ]),
    ("Open-Portmapper", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("Open-SNMP", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("System description", "sysdesc"),
        ]),
    ("Open-MSSQL", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Version", "version"),
        ("source.local_hostname", "Server Name"),
        ExtraColumn("Instance Name", "instance_name"),
        ExtraColumn("Amplification", "amplification"),
        ]),
    ("Open-Mongo DB", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Version", "version"),
        ExtraColumn("Databases (excerpt)", "visible_databases"),
        ]),
    ("Open-Chargen", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("Open-IPMI", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("Open-Net BIOS", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("NTP-Monitor", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Response size", "size"),
        ]),
    ("Open-Elasticsearch", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Elasticsearch version", "version"),
        ExtraColumn("Instance name", "name"),
        ]),
    ("Open-mDNS", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Services", "services"),
        ]),
    ("Open-Memcached", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Memcached version", "version"),
        ]),
    ("Open-Redis", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Redis version", "version"),
        ]),
    ("Open-SSDP", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("SSDP server", "server"),
        ]),
    ("Ssl-Freak-Scan", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ("source.reverse_dns", "Hostname"),
        ExtraColumn("Subject Name", "subject_common_name"),
        ExtraColumn("Issuer Name", "issuer_common_name"),
        ExtraColumn("FREAK Cipher", "freak_cipher_suite"),
        ]),
    ("Ssl-Scan", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ("source.reverse_dns", "Hostname"),
        ExtraColumn("Subject Name", "subject_common_name"),
        ExtraColumn("Issuer Name", "issuer_common_name"),
        ]),
    ])



def create_mails(cur, agg_notification, config, gpgme_ctx):
    """Create one or several email objects for an aggregated notification.

    Depending on the classification_type and format
    does the formatting and returns one or several emails with ids.

    :param config: script configuration
    :param agg_notification: the aggregated notification to create mails for
    :param cur: database cursor to use when loading event information

    :returns: list of tuples (email object, list of ids, ticket) with len >=1
    :rtype: list

    """

    email_tuples = []

    formatter = None

    if (agg_notification["format"] == "feed_specific"
        and agg_notification["feed_name"] in feed_specific_formats):
        formatter = mail_format_feed_specific_as_csv

    if formatter is not None:
        email_tuples = formatter(cur, agg_notification, config, gpgme_ctx)
    else:
        msg = ("Cannot generate emails for combination (%r, %r)"
               % (agg_notification["format"], agg_notification["feed_name"]))
        print(msg, file=sys.stderr)
        raise NotImplementedError(msg)

    return email_tuples

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

    # create from integer: fill with 0s and cut out 8 chars from the right
    num_str = "{:08d}".format(result[0]["nextval"])[-8:]
    ticket = "{:s}-{:s}".format(date_str, num_str)
    log.debug('New ticket number "{}".'.format(ticket,))

    return ticket


def mark_as_sent(cur, notification_ids, ticket):
    "Mark notifactions with given ids as sent and set the ticket number."
    log.debug("Marking notifications_ids {} as sent.".format(notification_ids))
    cur.execute(""" UPDATE notifications
                    SET sent_at = now(),
                        intelmq_ticket = %s
                  WHERE id = ANY (%s);""",
                (ticket, notification_ids,))


def send_notifications(config, notifications, cur):
    """
    Create and send notification mails for all items in notifications.

    All notifications that were successfully sent are marked as sent in
    the database. This function tries to make sure that this information
    can be committed as part of the transaction in progress even if
    errors occur during SQL statements executed by this function. The
    caller should also catch exceptions thrown by this method and always
    commit the transaction.

    :param config script configuration
    :param notifications a list of aggregated_notifications
    :param cur database cursor to use when loading event information

    :returns: number of send mails
    :rtype: int
    """
    sent_mails = 0
    gpgme_ctx = None

    if config["openpgp"]["always_sign"]:
        gpgme_ctx = gpgme.Context()
        signing_key = gpgme_ctx.get_key(config["openpgp"]["signing_key"])
        gpgme_ctx.signers = [signing_key]

    with smtplib.SMTP(host=config["smtp"]["host"],
                      port=config["smtp"]["port"]) as smtp:
        for notification in notifications:
            cur.execute("SAVEPOINT sendmail;")
            try:
                email_tuples = create_mails(cur, notification,
                                            config, gpgme_ctx)

                if len(email_tuples) < 1:
                    # TODO maybe use a user defined exception here?
                    raise RuntimeError("No emails for sending were generated!")
                for email_tuple in email_tuples:
                    smtp.send_message(email_tuple[0])
                    mark_as_sent(cur, email_tuple[1], email_tuple[2])
                    sent_mails += 1

            except:
                cur.execute("ROLLBACK TO SAVEPOINT sendmail;")
                raise
            finally:
                cur.execute("RELEASE SAVEPOINT sendmail;")
    return sent_mails


def get_pending_notifications(cur):
    """Retrieve all pending notifications from the database.
    Notifications are pending if they haven't been sent yet.
    Notifications are grouped by recipient, template, format,
    classification type and feed name so that the information about the
    events for which the notifications are sent can be aggregated.

    Also, the feed names 'Botnet-Drone-Hadoop', 'Sinkhole-HTTP-Drone'
    and 'Microsoft-Sinkhole' are replaced by 'generic_malware' before
    grouping so that event from those feeds are aggregated.

    :returns: list of aggreated notifications
    :rtype: list
    """
    cur.execute("""\
        SELECT n.email as email, n.template as template, n.format as format,
               n.classification_type as classification_type,
               n.feed_name AS feed_name,
               array_agg(n.events_id) as event_ids,
               array_agg(n.id) as notification_ids
          FROM (SELECT id, events_id, email, template, format,
                       classification_type, notification_interval,
                       CASE WHEN feed_name IN ('Botnet-Drone-Hadoop',
                                               'Sinkhole-HTTP-Drone',
                                               'Microsoft-Sinkhole')
                            THEN 'generic_malware'
                            ELSE feed_name
                       END AS feed_name
                  FROM notifications
                 WHERE intelmq_ticket IS NULL
                FOR UPDATE NOWAIT) n
      GROUP BY n.email, n.template, n.format, n.classification_type, n.feed_name
        HAVING coalesce((SELECT max(sent_at) FROM notifications n2
                         WHERE n2.email = n.email
                           AND n2.template = n.template
                           AND n2.format = n.format
                           AND n2.classification_type = n.classification_type
                           AND n2.feed_name = n.feed_name)
                        + max(n.notification_interval)
                        < CURRENT_TIMESTAMP,
                        TRUE);""")
    return cur.fetchall()


def generate_notifications_interactively(config, cur, notifications):
    batch_size = 10

    pending = notifications[:]
    while pending:
        batch, pending = pending[:batch_size], pending[batch_size:]
        print('Current batch (%d of %d total):'
              % (len(batch), len(batch) + len(pending)))
        for i in batch:
            print('    * {0} {1} ({2}, {3}): {4} events'.format(
                  i["email"],
                  i["template"],
                  i["format"],
                  i["feed_name"],
                  len(i["event_ids"]))
                  )
        valid_answers = ("c", "s", "a", "q")
        while True:
            answer = input("Options: [c]ontinue, "
                           "[s]end this batch, "
                           "send [a]ll, "
                           "[q]uit? ").strip()
            if answer not in valid_answers:
                print("Please enter one of the characters %s"
                      % ", ".join(valid_answers))
            else:
                break
        if answer == "c":
            print("Skipping this batch.")
            pass
        elif answer == "q":
            print("Exiting without sending any further mails.")
            pending = []
        else:
            to_send = batch
            if answer == "a":
                to_send.extend(pending)
                pending = []

            print("Sending mails for %d entries... " % (len(to_send),))
            sent_mails = send_notifications(config, to_send, cur)
            print("%d mails sent. " % (sent_mails,))


def mailgen(args, config):
    cur = None
    conn = open_db_connection(config)
    try:
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC';")
        agg_notifications = get_pending_notifications(cur)
        if not agg_notifications:
            print("No pending notifications to be sent")
            return

        if args.all:
            sent_mails = send_notifications(config, agg_notifications, cur)
            log.info("{:d} mails sent.".format(sent_mails))
        else:
            generate_notifications_interactively(config, cur,
                                                 agg_notifications)

    finally:
        if cur is not None:
            cur.close()
        # the only change to the database is marking the sent mails as
        # actually sent. We always want to commit that information even
        # when errors occur, so we're calling commit in the finally
        # block.
        conn.commit()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        prog=APPNAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=USAGE,
        description=DESCRIPTION,
        epilog=EPILOG,
        )
    parser.add_argument('-a', '--all', action='store_true',
                        help='Process all events (batch mode)')
    args = parser.parse_args()

    config = read_configuration()

    # checking openpgp config
    if "openpgp" not in config or {
            "always_sign", "gnupg_home", "signing_key"
            } != config["openpgp"].keys():
        log.critical("Config section openpgp missing or incomplete. Exiting.")
        exit(1)
    # setting up gnupg
    os.environ['GNUPGHOME'] = config["openpgp"]["gnupg_home"]

    mailgen(args, config)

# to lower the chance of problems like
# http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#the-double-import-trap
# we discourage calling this file directly as a "script", instead use
# the entry-point script by the temporary install or
# go to the right toplevel directory and use a full import like
#  python3 -c "from intelmqmail import cb; cb.main()"

