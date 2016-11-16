from intelmqmail.tableformat import build_table_formats, ExtraColumn


def list_csv_formats():
    return build_table_formats([
    ("csv_malware", [
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
    ("csv_DNS-open-resolvers", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Min. amplification", "min_amplification"),
        ]),
    ("csv_Open-Portmapper", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("csv_Open-SNMP", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("System description", "sysdesc"),
        ]),
    ("csv_Open-MSSQL", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Version", "version"),
        ("source.local_hostname", "Server Name"),
        ExtraColumn("Instance Name", "instance_name"),
        ExtraColumn("Amplification", "amplification"),
        ]),
    ("csv_Open-MongoDB", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Version", "version"),
        ExtraColumn("Databases (excerpt)", "visible_databases"),
        ]),
    ("csv_Open-Chargen", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("csv_Open-IPMI", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("csv_Open-NetBIOS", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ]),
    ("csv_NTP-Monitor", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Response size", "size"),
        ]),
    ("csv_Open-Elasticsearch", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Elasticsearch version", "version"),
        ExtraColumn("Instance name", "name"),
        ]),
    ("csv_Open-mDNS", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Workstation info", "workstation_info"),
        ]),
    ("csv_Open-Memcached", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Memcached version", "version"),
        ]),
    ("csv_Open-Redis", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("Redis version", "version"),
        ]),
    ("csv_Open-SSDP", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ExtraColumn("SSDP server", "server"),
        ]),
    ("csv_Ssl-Freak-Scan", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ("source.reverse_dns", "Hostname"),
        ExtraColumn("Subject Name", "subject_common_name"),
        ExtraColumn("Issuer Name", "issuer_common_name"),
        ExtraColumn("FREAK Cipher", "freak_cipher_suite"),
        ]),
    ("csv_Ssl-Scan", [
        ("source.asn", "ASN"),
        ("source.ip", "IP"),
        ("time.source", "Timestamp (UTC)"),
        ("source.reverse_dns", "Hostname"),
        ExtraColumn("Subject Name", "subject_common_name"),
        ExtraColumn("Issuer Name", "issuer_common_name"),
        ]),
    ])

