"""
This file provides a Key-Key Map for X-ARF-Keys and IntelMQ-Keys

This Mapping contains fields which are used in login-attack reports
"""

import intelmq_xarf_common as ixc

keys = ixc.common_keys + [
    ("Category", None), # Cannot be mapped, is always "abuse"
    ("Report-Type", None), # Cannot be mapped, is always "login-attack"
    ("Schema-URL", None), # has to be set to http://x-arf.org/schema/abuse_login-attack_0.1.2.json
    ("Source", "source.ip"),
    ("Source-Type", None), # Needs to be determined if ipv4 or ipv6 depending on source.ip
    ("Port", "source.port"),
    ("Destination", "destination.ip"), # Optional
    ("Destination-Type", None), # Optional, Needs to be determined if ipv4 or ipv6 depending on destination.ip
    ("Service", "application.protocoll"), #this is a wild guess. It's not guaranteed the field always exists in intelmq. The field "Service" is Mandatory!
]



taxonomies = [
    # this x-arf map applies to intelmq-taxonomies
    "Intrusion Attempts",
]

types = [
    # this x-arf map applies to intelmq-types
    # TODO
]
