"""Example script demonstrating a fallback notification directive handler.

This handler tries to handle all directives by formatting a simple email
with the event information in CSV format where the columns are limited
to event attributes that should be present in almost all events.
"""

from intelmqmail.tableformat import build_table_format
from intelmqmail.templates import Template

table_format = build_table_format(
    "Fallback",
    (("source.asn", "asn"),
     ("source.ip", "ip"),
     ("time.source", "timestamp"),
     ("source.port", "src_port"),
     ("destination.ip", "dst_ip"),
     ("destination.port", "dst_port"),
     ("destination.fqdn", "dst_host"),
     ("protocol.transport", "proto"),
     ))

# The text of the template is inlined here to make sure creating the
# mail does not fail due to a missing template file.
template = Template.from_strings("CB-Report#${ticket_number}",
                                 "Dear Sir or Madam,\n"
                                 "\n"
                                 "Please find below a list of affected systems"
                                 " on your network(s).\n"
                                 "\n"
                                 "Events:\n"
                                 "${events_as_csv}")

def create_notifications(context):
    # If there are some additional substitions to be performed in the
    # above template, add them to the substitition dictionary. By
    # passing it to the mail_format_as_csv method below they will be
    # substituted into the template when the mail is created.
    substitutions = dict()

    return context.mail_format_as_csv(table_format, template=template,
                                      substitutions=substitutions)
