
"""
This Script looks for xarf directives....
it is highly experimental
this Script expects a directive like:

    return Directive(template_name="bot-infection_0.2.0_unstable",
                     event_data_format="xarf",
                     notification_interval=0)


"""

class Formatter:

    def __init__(self, field, formatter=lambda x: x):
        self.field = field
        self.formatter = formatter

    def format(self, event):
        return self.formatter(event[self.field])



class XarfSchema:

    def __init__(self, static_fields, event_mapping):
        self.static_fields = static_fields
        self.event_mapping = event_mapping
        for key, value in self.event_mapping.items():
            if not isinstance(value, Formatter):
                value = Formatter(value)
            self.event_mapping[key] = value

    def event_columns(self):
        return [formatter.field for formatter in self.event_mapping.values()]

    def xarf_params(self, event):
        params = self.static_fields.copy()
        for key, formatter in self.event_mapping.items():
            formatted = formatter.format(event)
            if formatted is not None:
                params[key] = formatted
        return params

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
            'date': Formatter("time.source", str),
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
# underscore _ should be converted by the xarf lib:
# https://github.com/xarf/python-xarf/blob/master/pyxarf/xarf.py#L425



def create_notifications(context):
    maybe_xarf = context.directive["event_data_format"]
    maybe_xarf_schema = context.directive["template_name"]

    xarf_schema = known_xarf_schema.get(maybe_xarf_schema, None)

    if maybe_xarf == "xarf" and xarf_schema is not None:
        return context.mail_format_as_xarf(xarf_schema)
    elif maybe_xarf and xarf_schema is None:
        # XARF was defined, but the schema is not configured.
        raise # TODO proper handling

    return None
