from intelmqmail.tableformat import build_table_formats, ExtraColumn


def list_csv_formats():
    return build_table_formats([
    ("csv_malware", [
        # this is used for the following feeds:
        #   "Botnet-Drone-Hadoop", "Sinkhole-HTTP-Drone",
        #   "Microsoft-Sinkhole"
        # These names are all mapped to "csv_malware" by the rule expert bot
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ("classification.identifier", "malware"),
        ("source.port", "src_port"),
        ("destination.ip", "dst_ip"),
        ("destination.port", "dst_port"),
        ("destination.fqdn", "dst_host"),
        ("protocol.transport", "proto"),
        ]),
    ("csv_DNS-open-resolvers", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ]),
    ("csv_Open-Portmapper", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ]),
    ("csv_Open-SNMP", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("system_desc", "sysdesc"),
        ]),
    ("csv_Open-LDAP", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("dns_hostname", "dns_host_name"),
        ]),
    ("csv_Open-MSSQL", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("mssql_version", "version"),
        ("source.local_hostname", "server_name"),
        ExtraColumn("instance_name", "instance_name"),
        ]),
    ("csv_Open-MongoDB", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("mongodb_version", "version"),
        ExtraColumn("visible_db_excerpt", "visible_databases"),
        ]),
    ("csv_Open-Chargen", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ]),
    ("csv_Open-IPMI", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ]),
    ("csv_Open-NetBIOS", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("workgroup_name", "workgroup"),
        ExtraColumn("machine_name", "machine_name"),
        ]),
    ("csv_NTP-Monitor", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ]),
    ("csv_Open-Elasticsearch", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("elasticsearch_version", "version"),
        ExtraColumn("instance_name", "name"),
        ]),
    ("csv_Open-mDNS", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("workstation_info", "workstation_info"),
        ]),
    ("csv_Open-Memcached", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("memcached_version", "version"),
        ]),
    ("csv_Open-Redis", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("redis_version", "version"),
        ]),
    ("csv_Open-SSDP", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ExtraColumn("ssdp_server", "server"),
        ]),
    ("csv_Ssl-Freak-Scan", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ("source.reverse_dns", "hostname"),
        ExtraColumn("subject_common_name", "subject_common_name"),
        ExtraColumn("issuer_common_name", "issuer_common_name"),
        ExtraColumn("freak_cipher_suite", "freak_cipher_suite"),
        ]),
    ("csv_Ssl-Scan", [
        ("source.asn", "asn"),
        ("source.ip", "ip"),
        ("time.source", "timestamp"),
        ("source.reverse_dns", "hostname"),
        ExtraColumn("subject_common_name", "subject_common_name"),
        ExtraColumn("issuer_common_name", "issuer_common_name"),
        ]),
    ])

