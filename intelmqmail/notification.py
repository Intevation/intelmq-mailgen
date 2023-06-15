""" Notification related functionality.

SPDX-License-Identifier: AGPL-3.0-or-later
SPDX-FileCopyrightText: Copyright (C) 2016, 2021 by Bundesamt für Sicherheit in der Informationstechnik
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
    * Bernhard Herzog <bernhard.herzog@intevation.de>
    * Dustin Demuth
"""  # noqa
import os
import tempfile
import datetime

from typing import Dict, Optional

# if we have the optional module pyxarf, we can define more methods
try:
    import pyxarf
except ModuleNotFoundError:
    pyxarf = None

from intelmqmail.db import load_events, new_ticket_number, mark_as_sent
from intelmqmail.templates import read_template, Template
from intelmqmail.tableformat import format_as_csv
from intelmqmail.mail import create_mail, clearsign, domain_from_sender


class NotificationError(Exception):
    """Base class for notification related exceptions"""


class InvalidDirective(NotificationError):
    """Indicates an invalid notification directive.

    Scripts should raise this exception while processing a directive if
    they have determined that they should handle the directive but
    cannot because of a defect in the directive. Directives can be
    invalid for various reasons, e.g. by referring to unknown CSV
    formats or templates.
    """


class InvalidTemplate(InvalidDirective):
    """Indicates a problem with a template needed for a directive.
    """

    def __init__(self, template_name):
        self.template_name = template_name
        super().__init__(f"Invalid template {self.template_name!r}")


class Directive:
    """The directives for which notifications have to be created.

    This is the mailgen counterpart to the Directive class in the rule
    expert bot in IntelMQ which adds notification directives to the
    events. The main difference is that this class represents a
    collection of those directives. The directives in the collection
    share all of the attributes that were assigned to them by the rules
    in the rule bot and those are available as instance variables with
    the same name in this class, with few exceptions. The exceptions are
    that the attribute ``medium`` is not present here because it's
    always ``'email'`` in mailgen and the ``aggregate_key`` and
    ``aggregate_fields`` attributes are available as one dictionary in
    the :py:attr:`aggregate_identifier` attribute (see also the
    :py:meth:`get_aggregation_item` method). There are also some attributes
    specific to this class: :py:attr:`inserted_at`,
    :py:attr:`last_sent`, :py:attr:`event_ids`,
    :py:attr:`directive_ids`. See below for their documentation.

    Attributes:
        recipient_address (str): The email address of the recipient.
        template_name (str): The name of the template for the contents
            of the notification.
        notification_format (str): The main format of the notification.
        event_data_format (str): The format to use for event data
            included in the notification.
        aggregate_identifier (dict): Additional key/value pairs used
            when aggregating directives. Both keys and values are strings.
        notification_interval (int): Interval between notifications for
            similar events. Can be used together with last_sent to
            determine whether this interval has expired.
        last_sent (datetime): When the last notification with the same
            attributes was sent.
        inserted_at (datetime): When the newest of the directive was
            inserted into the event DB. This can be useful instead of or
            in addition to last_sent and notification_interval.
        event_ids (list of int): The database ids of all events for
            which the directives were created.
        directive_ids (list of int): The database ids of the directives
            aggregated in this object.
    """

    def __init__(self, recipient_address, template_name, notification_format,
                 event_data_format, aggregate_identifier, event_ids,
                 directive_ids, inserted_at, notification_interval, last_sent):
        self.recipient_address = recipient_address
        self.template_name = template_name
        self.notification_format = notification_format
        self.event_data_format = event_data_format
        self.aggregate_identifier = dict(aggregate_identifier)
        self.event_ids = event_ids
        self.directive_ids = directive_ids
        self.inserted_at = inserted_at
        self.notification_interval = notification_interval
        self.last_sent = last_sent

    def __getitem__(self, key):
        """Dict-like interface for backwards compatibility"""
        return self.__dict__[key]

    def get(self, key):
        """Dict-like interface for backwards compatibility"""
        return self.__dict__.get(key)

    def get_aggregation_item(self, key):
        """Lookup an item in the aggregate_identifier.
        If the key is present in :py:attr:`aggregate_identifier` return
        it, return ``None`` otherwise.
        """
        return self.aggregate_identifier.get(key)


def parse_timestamp(raw):
    """Parse a timestamp that was stored in an IntelMQ-event as a string.
    This applies to e.g. time.observation. In particular, if such values
    are used for the aggregation of directives because than they are
    also stored as strings in the database.

    This function assumes that the timestamps use the ISO format
    produced by the isoformat() method of Python's datetime objects with
    an explicit time-zone offset of +00:00 but optional microseconds.
    """
    try:
        t = datetime.datetime.strptime(raw, '%Y-%m-%dT%H:%M:%S+00:00')
    except ValueError:
        t = datetime.datetime.strptime(raw, '%Y-%m-%dT%H:%M:%S.%f+00:00')
    return t.replace(tzinfo=datetime.timezone.utc)


class ScriptContext:
    """Provide the context in which scripts are run.

    The ScriptContext objects provide access to the details of the
    directives the scripts are to create notifications for and to the
    environment in which to do it, such as configuration settings.

    Attributes:
        directive: The aggregated directive for which the script has to
            produce a notification
        config: the mailgen configuration
        logger: the logger the script should use for logging
    """

    def __init__(self, config, cur, gpgme_ctx, directive, logger, template: Optional[Template] = None, templates: Optional[Dict[str, Template]] = None):
        self.config = config
        self.db_cursor = cur
        self.gpgme_ctx = gpgme_ctx
        self.directive = directive
        self.logger = logger
        self.now = datetime.datetime.now(datetime.timezone.utc)
        self.fallback_template: Optional[Template] = template
        self.templates: Optional[Dict[str, Template]] = templates

    def notification_interval_exceeded(self):
        """Return whether the notification interval has been exceeded.
        This method looks at the directive attributes last_sent and
        notification_interval and returns whether more time than the
        notification_interval has passed since the last_sent time. A
        last_sent time of None, indicating that no similar notification
        has been sent yet, counts as the interval having been exceeded,
        i.e. this method returns true in that case.
        """
        last_sent = self.directive.last_sent
        notification_interval = self.directive.notification_interval
        return (last_sent is None or
                (last_sent + notification_interval < self.now))

    def age_of_newest_directive(self):
        """Return the age of the newest directive in the group.
        The age is the difference between now and the directive's
        inserted_at attribute as a timedelta object.
        """
        return self.now - self.directive.inserted_at

    def age_of_observation(self):
        """Return the age of the events that led to the directives.
        The age of the events is the difference between now and the
        value of the time.observation field of the events as a timedelta
        object.

        NOTE: This can only be determined if the directives are
        aggregated by time.observation. Otherwise the necessary
        information is not available when the directives are processed
        by mailgen.

        If time.observation cannot be determined this method returns a
        None.
        """
        time_observation = self.directive.get_aggregation_item(
            "time.observation")
        if time_observation is not None:
            return self.now - parse_timestamp(time_observation)

        return None

    def new_ticket_number(self):
        return new_ticket_number(self.db_cursor)

    def load_events(self, columns=None):
        return load_events(self.db_cursor, self.directive.event_ids, columns)

    def read_template(self, templates: Dict[str, Template]) -> Template:
        template_name = ''
        try:
            template_name = self.directive.template_name
            try:
                return templates[template_name]
            except KeyError:
                return read_template(self.config["template_dir"], template_name)
            finally:
                self.logger.debug('Using template name %r.', template_name)
        except Exception as e:
            raise InvalidTemplate(template_name) from e

    def maybe_sign(self, body):
        if self.gpgme_ctx:
            body = clearsign(self.gpgme_ctx, body)
        return body

    def mail_format_as_csv(self, format_spec, template=None,
                           substitutions=None, attach_event_data=False,
                           template_name=None):
        """Create an email with the event data formatted as CSV.

        The subject and body of the mail are taken from a template. The
        template can use the following substitutions by default:

            ticket_number: The ticket number assigned by mailgen for the
                notification.
            events_as_csv: The event data formatted as CSV

        If the notification directives specify special aggregation
        criteria, these are also available. Which these are precisely
        depends on the directives, but a common case is to aggregate
        notifications for events that share some information, so if the
        directives specify aggregation by source.asn, this substitution is
        also available.

        Args:
            format_spec (TableFormat): a description of the CSV format
                as an instance of :py:class:`TableFormat`.
            template (Template): The template object for the subject and
                body of the mail. If omitted or None, the directive's
                template_name will be used to load the template. See
                :py:meth:`read_template`.
            substitutions (dict): Dictionary mapping strings to strings
                with substitutions. These will be available in templates
                in addition to the ones made available by this method.
            attach_event_data (bool): If true the CSV formatted event
                data will be included in the mail as attachment.
            template_name: The file name of the template inside
                "template_dir"

        Return:
            list of EmailNotification instances. The list has one
            element. It's a list so that it can be used directly as a
            return value of a notification script's create_notifications
            function.
        """
        events = self.load_events(format_spec.event_table_columns())

        events_as_csv = format_as_csv(format_spec, events)

        # default: use parameter `template`
        if template is None and template_name:  # Use template name if given
            template = read_template(self.config["template_dir"], template_name, templates=self.templates)
        elif template is None and self.fallback_template:  # Fallback to fallback template of Context
            template = self.fallback_template
        elif template is None:
            template = self.read_template(templates=self.templates)

        ticket = self.new_ticket_number()

        if substitutions is None:
            substitutions = {}
        else:
            substitutions = substitutions.copy()

        substitutions["ticket_number"] = ticket
        substitutions["events_as_csv"] = (
            events_as_csv if not attach_event_data else "")

        # Add the information on which the aggregation was based. These are
        # the same in all directives and events that led to this
        # notification, so it can be useful to refer to them in the message
        substitutions.update(self.directive.aggregate_identifier)

        subject, body = template.substitute(substitutions)

        attachments = []
        if attach_event_data:
            attachments.append(((events_as_csv,),
                                dict(subtype="csv", filename="events.csv")))

        mail = create_mail(sender=self.config["sender"],
                           recipient=self.directive.recipient_address,
                           subject=subject, body=body,
                           attachments=attachments, gpgme_ctx=self.gpgme_ctx)
        return [EmailNotification(self.directive, mail, ticket)]

    if pyxarf:
        def mail_format_as_xarf(self, xarf_schema):  # noqa
            """Create Messages in X-Arf Format

            Args:
                xarf_schema: an XarfSchema object, like in 20xarf.py

            Only defined, if the optional module pyxarf is available.

            Returns:
            """
            # Load the events and their required columns.
            # xarf_schema.event_columns() returns a dict/set/list of column-names
            events = self.load_events(xarf_schema.event_columns())

            sender = self.config["sender"]

            # Read the path to cache X-Arf Schemata from conf
            # if the variable was not set use a tempdir
            schema_cache = self.config.get("xarf_schemacache",
                                           tempfile.gettempdir() + os.sep)

            # This automatism is setting the Domain-Part within the
            # report_id of the X-ARF Report. If the parameter
            # xarf_reportdomain was not set in the the config, the senders
            # domain name is used.
            reportid_domain = self.config.get("xarf_reportdomain",
                                              domain_from_sender(sender))

            template = self.read_template()

            returnlist_notifications = []

            # Create an X-Arf Message for every event
            for event in events:
                # Get a new ticketnumber for each event
                ticket = self.new_ticket_number()
                report_id = "{}@{}".format(ticket, reportid_domain)

                subject, body = template.substitute({"ticket_number": ticket})

                params = {
                    'schema_cache': schema_cache,
                    'reported_from': sender,
                    'report_id': report_id,
                    # 'useragent': "IntelMQ-Mailgen,  # Useragent is set by pyxarf __useragent__  # noqa
                    }
                # now, as we know the events data and the intelmq-fields and
                # the mapping of these fields to the X-ARF Schema, pass the
                # event into the XarfSchema's xarf_params function in order
                # to resolve mapping of the events data to the X-Arf-Key
                params.update(xarf_schema.xarf_params(event))

                # Create an X-ARF Message using the pyxarf library.
                # The lib downloads the schema from schema_url automagically
                # and stores it in the schema_cache
                xarf_object = pyxarf.Xarf(**params)

                mail = self.create_xarf_mail(subject, body, xarf_object)

                returnlist_notifications.append(EmailNotification(self.directive,
                                                                  mail, ticket))

            return returnlist_notifications

    if pyxarf:
        def create_xarf_mail(self, subject, body, xarf_object):  # noqa
            """

            Args:
                xarf_object:

            Only defined, if the optional module pyxarf is available.

            Returns:

            """
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.utils import formatdate

            msg = MIMEMultipart()
            msg.attach(MIMEText(body))
            msg.attach(MIMEText(xarf_object.to_yaml('machine_readable'), 'plain',
                                'utf-8'))

            msg.add_header("From", self.config["sender"])
            msg.add_header("To", self.directive.recipient_address)
            msg.add_header("Subject", subject)
            msg.add_header("Auto-Submitted", "auto-generated")
            msg.add_header("X-ARF", "PLAIN")  # TODO BULK IS NOT SUPPORTED YET
            msg.add_header("Date", formatdate(timeval=None, localtime=True))

            return msg


class SendContext:

    def __init__(self, cur, smtp):
        self.cur = cur
        self.smtp = smtp

    def mark_as_sent(self, directive_ids, ticket, sent_at):
        mark_as_sent(self.cur, directive_ids, ticket, sent_at)


class Notification:

    def __init__(self, directive):
        self.directive = directive

    def send(self, context):
        pass


class EmailNotification(Notification):

    def __init__(self, directive, email, ticket):
        self.email = email
        self.ticket = ticket
        super().__init__(directive)

    def send(self, send_context):
        send_context.smtp.send_message(self.email)
        send_context.mark_as_sent(self.directive.directive_ids, self.ticket,
                                  self.email["Date"].datetime)

    def __repr__(self) -> str:
        return f'EmailNotification(email={self.email!r}, ticket={self.ticket!r})'


class _Postponed:
    """Represents a script result for postponed directives.

    There's one predefined instance, Postponed, which should be used as
    the return value of the create_notifications function in scripts to
    indicate that the script could produce emails for the directive
    being processed but that it did not actually produce any mails
    because the directive cannot be processed yet because not all
    condititions have been met yet.

    A common condition is that sufficient time (> notification_interval)
    must have passed since the previous similar notification. The
    create_notifications function can use the context's
    notification_interval_exceeded method to determine whether enough
    time has passed and in case it hasn't, return Postponed.
    """

    def __bool__(self):
        return True

    def __len__(self):
        return 0

    def __iter__(self):
        return iter([])


Postponed = _Postponed()
