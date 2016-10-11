"""
This file provides a Key-Key Map for X-ARF-Keys and IntelMQ-Keys

This Mapping contains fields which are used in login-attack reports

Most likely this will not be used with IntelMQ
"""

import intelmq_xarf_common as ixc

keys = ixc.common_keys + [
    ("Category", None), # Cannot be mapped, is always "info"
    ("Report-Type", None), # Cannot be mapped, is one of "dnsbl-listing","dnsbl-listed","dnsbl-delisted"
    ("Schema-URL", None), # has to be set to http://x-arf.org/schema/info_dnsbl_0.1.0.json
    ("Source", None), # Source.ip or source.fqdn
    ("Source-Type", None), # Needs to be determined depending on Source
    ("DNSBL-Record", None), # IP-Address, Optional
    ("DNSBL", None), # a URI
]



taxonomies = [
    # this x-arf map applies to intelmq-taxonomies
    # TODO
]

types = [
    # this x-arf map applies to intelmq-types
    # TODO
]

