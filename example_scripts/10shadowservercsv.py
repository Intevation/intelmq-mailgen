import copy

from intelmqmail.tableformat import build_table_formats, ExtraColumn
from intelmqmail.notification import Postponed


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
    ("csv_malware", [
        # this is used for the following feeds:
        #   "Botnet-Drone-Hadoop", "Sinkhole-HTTP-Drone",
        #   "Microsoft-Sinkhole"
        # These names are all mapped to "csv_malware" by the rule expert bot
        "source.asn",
        "source.ip",
        "time.source",
        "classification.identifier",
        "source.port",
        "destination.ip",
        "destination.port",
        "destination.fqdn",
        "protocol.transport",
        ]),
    ("csv_DNS-open-resolvers", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("csv_Open-Portmapper", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("csv_Open-SNMP", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:system_desc",
        ]),
    ("csv_Open-LDAP", [
        "source.asn",
        "source.ip",
        "time.source",
        ("source.local_hostname", "dns_hostname"),
        ]),
    ("csv_Open-MSSQL", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:mssql_version",
        "source.local_hostname",
        ExtraColumn("instance_name", "instance_name"),
        ]),
    ("csv_Open-MongoDB", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:mongodb_version",
        ]),
    ("csv_Open-Chargen", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("csv_Open-IPMI", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("csv_Open-NetBIOS", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:workgroup_name",
        "extra:machine_name",
        ]),
    ("csv_NTP-Monitor", [
        "source.asn",
        "source.ip",
        "time.source",
        ]),
    ("csv_Open-Elasticsearch", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:elasticsearch_version",
        ExtraColumn("instance_name", "name"),
        ]),
    ("csv_Open-mDNS", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:workstation_info",
        ]),
    ("csv_Open-Memcached", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:memcached_version",
        ]),
    ("csv_Open-Redis", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:redis_version",
        ]),
    ("csv_Open-SSDP", [
        "source.asn",
        "source.ip",
        "time.source",
        "extra:ssdp_server",
        ]),
    ("csv_Ssl-Freak-Scan", [
        "source.asn",
        "source.ip",
        "time.source",
        "source.reverse_dns",
        "extra:subject_common_name",
        "extra:issuer_common_name",
        "extra:freak_cipher_suite",
        ]),
    ("csv_Ssl-Scan", [
        "source.asn",
        "source.ip",
        "time.source",
        "source.reverse_dns",
        "extra:subject_common_name",
        "extra:issuer_common_name",
        ]),
    ])


def create_notifications(context):
    """

    Args:
        context:

    Returns:

    """
    if context.directive["notification_format"] == "shadowserver":

        # Copy substitutions from the context.
        # This way we can edit the variables in this script
        # without changing the context.
        substitution_variables = copy.copy(context.substitutions)

        format_spec = table_formats.get(context.directive["event_data_format"])
        if format_spec is not None:
            if not context.notification_interval_exceeded():
                return Postponed

            substitution_variables["data_location_en"] = substitution_variables["data_location_inline_en"]
            substitution_variables["data_location_de"] = substitution_variables["data_location_inline_de"]
            return context.mail_format_as_csv(format_spec, substitutions=substitution_variables)

    return None
