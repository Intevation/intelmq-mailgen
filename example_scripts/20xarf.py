"""X-ARF for IntelMQ-Mailgen

This script looks for xarf directives within IntelMQ-Mailgen's context
objects. To be successful, it expects a directive which was created by
an *IntelMQ CertBUND-Contact Rule Expert* like::

    return Directive(template_name="bot-infection_0.2.0_unstable",
                     event_data_format="xarf",
                     notification_interval=0)
"""

from email.utils import formatdate  # required for RFC2822 date-conversion


class Formatter:
    """A Formatter which converts data into an other representation.

    This is a formatter which is used to combine information on the
    IntelMQ-field which should be inserted into the X-Arf Message and a
    Function which is converting this data into an X-Arf compliant
    format
    """

    def __init__(self, field, formatter=lambda x: x):
        """Initialise the formatter

        Args:
            field: The name of the IntelMQ field, for instance "source.ip"
            formatter: a function which should be used to format the
                data of the IntelMQ field
        """
        self.field = field
        self.formatter = formatter

    def format(self, event):
        """Apply the formatting function to the data

        Args:
            event: An IntelMQ Event

        Returns:
            The formatted value of self.field
        """
        return self.formatter(event[self.field])


class XarfSchema:
    """XarfSchema handles X-Arf Schema definitions

    This class provides functions that are necesaary to handle the
    X-ARF Schema definitions provided below.
    """

    def __init__(self, static_fields, event_mapping):
        """Initialise the Schema Object

        Args:

            static_fields: A dictionary of static fields, which are
                typical to X-Arf messages of this schema

            event_mapping: A dictionary of X-Arf-Key / Formatter pairs.
                Each Formatter contains the field-name of the
                IntelMQ-Event. Each X-Arf-Key contains the name of the
                X-Arf Field
        """
        self.static_fields = static_fields
        self.event_mapping = event_mapping
        for key, value in self.event_mapping.items():
            if not isinstance(value, Formatter):
                value = Formatter(value)
            self.event_mapping[key] = value

    def event_columns(self):
        """This returns the fieldname of the event-mappings Formatter-Object

        Returns:
            A field name. For instance "source.ip"
        """
        return [formatter.field for formatter in self.event_mapping.values()]

    def xarf_params(self, event):
        """Create X-ARF key-value pairs

        Generates a dictionary of key-value pairs, where key is the name
        of the X-ARF field, and value is the data of the IntelMQ-Event.
        The function formats the data to the correct format, by using
        the formatting funtions which have been provided within the
        schema-definitions below.

        Args:
            event: An IntelMQ-Event

        Returns:
            A dictionary containing the X-Arf-fieldname to event-data
            mapping after the formatting-function was applied.
        """
        params = self.static_fields.copy()
        for key, formatter in self.event_mapping.items():
            formatted = formatter.format(event)
            if formatted is not None:
                # Only add non-Null values to the dict
                params[key] = formatted
        return params


def datetime_to_rfc3339(eventdatetime):
    """Convert datetime object to `RFC3339 <https://www.ietf.org/rfc/rfc3339.txt>`_ string

    Hint: when using python > 3.6 one could use timespec='seconds' to
    truncate the result to seconds...

    Args:
        eventdatetime: A datetime-object with timezone information

    Returns:
        the datetime as a `RFC3339
        <https://www.ietf.org/rfc/rfc3339.txt>`_ encoded string
    """
    return eventdatetime.astimezone().isoformat()


def datetime_to_rfc2822(eventdatetime):
    """Convert datetime object to `RFC2822 <https://www.ietf.org/rfc/rfc2822.txt>`_ string

    Args:
        eventdatetime: A datetime-object with timezone information

    Returns:
        the datetime as a `RFC2822
        <https://www.ietf.org/rfc/rfc2822.txt>`_ encoded string
    """
    return formatdate(eventdatetime.timestamp(), localtime=True)


known_xarf_schema = {
    "bot-infection_0.2.0_unstable": XarfSchema({
        'schema_url': 'https://raw.githubusercontent.com/Intevation/xarf-schemata/master/abuse_bot-infection_0.2.0_unstable.json',
        'category': 'abuse',
        'report_type': 'bot-infection',
        'source_type': 'ip-address',
        'destination_type': 'ip-address',
        'attachment': None,
    },
    {
        'source': 'source.ip',
        'source_port': 'source.port',
        'source_asn': 'source.asn',
        'date': Formatter("time.source", datetime_to_rfc3339),
        'destination': 'destination.ip',
        'destination_port': 'destination.port',
        'destination_asn': 'destination.asn',
        'classification_taxonomy': 'classification.taxonomy',
        'classification_type': 'classification.type',
        'classification_identifier': 'classification.identifier',
        'malware_name': 'malware.name',
        'malware_md5': 'malware.hash.md5',
    })
}

"""known_xarf_schema is a dictionary containing the mapping-dictionaries of
X-ARF Fields to IntelMQ-Fields

Each X-Arf-Schema is divided into two discrete dictionaries.

 1. "Static" Fields: These fields are the same in each X-ARF-Message of
    the given schema
 2. "Event-Mapping" fields: This is a dictionary providing the mapping
    of an IntelMQ field to the X-ARF Message.

Example:
    The IntelMQ field "source.ip" will be converted to the field
    "source" in the X-ARF Message. As a direct conversation is not
    possible in all cases, you can user formatters, like the
    `datetime_to_rfc3339` formatter in order to convert the data
    retrieved from the IntelMQ-Event::

        "bot-infection_0.2.0_unstable": XarfSchema({
            'schema_url': 'https://raw.githubusercontent.com/Intevation/xarf-schemata/master/abuse_bot-infection_0.2.0_unstable.json',
        },
        {
            'source': 'source.ip',
            'date': Formatter("time.source", datetime_to_rfc3339),
        })

Note:
    The underscores `_` in the keys will be converted into dashes `-` by
    the xarf-library `pyxarf
    <https://github.com/xarf/python-xarf/blob/master/pyxarf/xarf.py#L425>`_
"""


def create_notifications(context):
    """Entrypoint of intelmq-mailgen.

    Args:
        context:

    Returns:

    """
    maybe_xarf = context.directive["event_data_format"]
    maybe_xarf_schema = context.directive["template_name"]

    xarf_schema = known_xarf_schema.get(maybe_xarf_schema, None)

    if maybe_xarf == "xarf" and xarf_schema is not None:
        return context.mail_format_as_xarf(xarf_schema)
    elif maybe_xarf and xarf_schema is None:
        # XARF was defined, but the schema is not configured.
        raise  # TODO proper handling

    return None
