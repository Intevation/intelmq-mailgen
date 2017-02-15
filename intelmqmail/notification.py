from intelmqmail.db import load_events, new_ticket_number, mark_as_sent
from intelmqmail.templates import read_template
from intelmqmail.tableformat import format_as_csv
from intelmqmail.mail import create_mail, clearsign


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
        super().__init__("Invalid template %r" % (self.template_name,))


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

    def __init__(self, config, cur, gpgme_ctx, directive, logger):
        self.config = config
        self.db_cursor = cur
        self.gpgme_ctx = gpgme_ctx
        self.directive = directive
        self.logger = logger

    def new_ticket_number(self):
        return new_ticket_number(self.db_cursor)

    def load_events(self, columns=None):
        return load_events(self.db_cursor, self.directive["event_ids"], columns)

    def read_template(self):
        try:
            template_name = self.directive["template_name"]
            return read_template(self.config["template_dir"], template_name)
        except Exception as e:
            raise InvalidTemplate(template_name) from e

    def maybe_sign(self, body):
        if self.gpgme_ctx:
            body = clearsign(self.gpgme_ctx, body)
        return body

    def mail_format_as_csv(self, format_spec, template=None,
                           substitutions=None):
        events = self.load_events(format_spec.event_table_columns())

        events_as_csv = format_as_csv(format_spec, events)

        if template is None:
            template = self.read_template()

        ticket = self.new_ticket_number()

        if substitutions is None:
            substitutions = {}
        else:
            substitutions = substitutions.copy()

        substitutions["ticket_number"] = ticket
        substitutions["events_as_csv"] = events_as_csv

        # Add the information on which the aggregation was based. These are
        # the same in all directives and events that led to this
        # notification, so it can be useful to refer to them in the message
        for key, value in self.directive["aggregate_identifier"]:
            substitutions[key] = value

        subject, body = template.substitute(substitutions)

        body = self.maybe_sign(body)

        mail = create_mail(sender=self.config["sender"],
                           recipient=self.directive["recipient_address"],
                           subject=subject, body=body,
                           attachments=[])
        return [EmailNotification(self.directive, mail, ticket)]



class SendContext:

    def __init__(self, cur, smtp):
        self.cur = cur
        self.smtp = smtp

    def mark_as_sent(self, directive_ids, ticket):
        mark_as_sent(self.cur, directive_ids, ticket)


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
        send_context.mark_as_sent(self.directive["directive_ids"], self.ticket)
