from intelmqmail.tableformat import build_table_formats, ExtraColumn
from intelmqmail.notification import Postponed

import copy

standard_column_titles = {
    # column titles for standard event attributes
    'classification.identifier': 'malware',
    'destination.fqdn': 'dst_host',
    'destination.ip': 'dst_ip',
    'destination.port': 'dst_port',
    'protocol.transport': 'proto',
    'source.asn': 'asn',
    'source.ip': 'ip',
    'source.local_hostname': 'server_name',
    'source.port': 'src_port',
    'source.reverse_dns': 'hostname',
    'time.source': 'timestamp',

    # column titles for extra attributes
    'extra:system_desc': 'sysdesc',
    "extra:mssql_version": "version",
    "extra:mongodb_version": "version",
    "extra:workgroup_name": "workgroup",
    "extra:machine_name": "machine_name",
    "extra:elasticsearch_version": "version",
    "extra:workstation_info": "workstation_info",
    "extra:memcached_version": "version",
    "extra:redis_version": "version",
    "extra:ssdp_server": "server",
    "extra:subject_common_name": "subject_common_name",
    "extra:issuer_common_name": "issuer_common_name",
    "extra:freak_cipher_suite": "freak_cipher_suite",
}


def add_default_titles(columns):
    """
    Add the standard title to each of the columns.

    Args:
        columns:

    Returns:

    """
    extended_columns = []
    for col in columns:
        if isinstance(col, str):
            title = standard_column_titles[col]
            if col.startswith("extra:"):
                extended_columns.append(ExtraColumn(col[6:], title))
            else:
                extended_columns.append((col, title))
        else:
            extended_columns.append(col)
    return extended_columns


def table_formats_with_default_titles(formats):
    """
    Frontend for build_table_formats that adds standard column titles.

    Args:
        formats:

    Returns:

    """

    return build_table_formats([(name, add_default_titles(columns))
                                for name, columns in formats])

table_formats = table_formats_with_default_titles([
    ("opendns", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("openportmapper", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("opensnmp", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:system_desc",
        ]),
    ("openldap", [
        "source.asn",
        "source.ip",
        "time.source",
        ("source.local_hostname", "dns_hostname"),
        ]),
    ("openmssql", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:mssql_version",
        "source.local_hostname",
        ExtraColumn("instance_name", "instance_name"),
        ]),
    ("openmongodb", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:mongodb_version",
        ]),
    ("openchargen", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("openipmi", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("opennetbios", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:workgroup_name",
        "extra:machine_name",
        ]),
    ("openntp", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("openelasticsearch", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:elasticsearch_version",
        ExtraColumn("instance_name", "name"),
        ]),
    ("openmdns", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:workstation_info",
        ]),
    ("openmemcached", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:memcached_version",
        ]),
    ("openredis", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:redis_version",
        ]),
    ("openssdp", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:ssdp_server",
        ]),
    ("ssl-freak", [
        "source.asn",
        "source.ip",
        "time.source",
        "source.reverse_dns",
        "extra:subject_common_name",
        "extra:issuer_common_name",
        "extra:freak_cipher_suite",
        ]),
    ("ssl-poodle", [
        "source.asn",
        "source.ip",
        "time.source",
        "source.reverse_dns",
        "extra:subject_common_name",
        "extra:issuer_common_name",
        ]),
    ])


def create_notifications(context):

    if context.directive["notification_format"] == "vulnerable-service":

        if not context.notification_interval_exceeded():
            return Postponed

        # Copy Substitutions from the context to this script.
        # This way we can edit the variables in this script
        # without changing the context.
        substitution_variables = copy.copy(context.substitutions)

        data_format = context.directive["event_data_format"]
        template_name = context.directive["template_name"]

        # The template name is expected to look like
        # openportmapper_provider
        # which is sth. like the lowercase classification.identifier
        # and the target group.
        # If the classification.identifier contains underscores,
        # we'll ge in trouble here. You need to make sure in
        # the scripts generating the directives, that this does never
        # happen.
        csv_header_style = template_name.split(sep='_')[0]

        format_spec = table_formats.get(csv_header_style)

        return create_csv_mail(data_format, format_spec, substitution_variables, context)

    return None


def create_csv_mail(data_format, csv_format, substitution_variables, context):
    if data_format.endswith("_csv_inline"):
        # If Inline-Messages are wanted
        substitution_variables["data_location_en"] = substitution_variables["data_location_inline_en"]
        substitution_variables["data_location_de"] = substitution_variables["data_location_inline_de"]
        return context.mail_format_as_csv(csv_format, substitutions=substitution_variables)

    elif data_format.endswith("_csv_attachment"):
        # TODO There is no attachment, yet!
        substitution_variables["data_location_en"] = substitution_variables["data_location_attached_en"]
        substitution_variables["data_location_de"] = substitution_variables["data_location_attached_de"]
        substitution_variables["data_inline_separator_en"] = ""
        substitution_variables["data_inline_separator_de"] = ""
        return context.mail_format_as_csv(csv_format, substitutions=substitution_variables,
                                          attach_event_data=True)
