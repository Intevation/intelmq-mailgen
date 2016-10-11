"""
This file provides a Key-Key Map for X-ARF-Keys and IntelMQ-Keys

This Mapping contains fields which are used in fraud reports
"""

import intelmq_xarf_common as ixc

keys = ixc.common_keys + [
    ("Category", None), # Cannot be mapped, is always "abuse"
    ("Report-Type", None), # TODO needs to be derived, see below. always "phishing|infected|defacement|scam|spam"
    ("Schema-URL", None), # has to be set to http://x-arf.org/schema/fraud_0.1.4.json
    ("Source", None), # This can be multiple things: source.ip or source.url
    ("Source-Type", None), # Needs to be determined if ipv4 or ipv6 depending on source.ip
    ("Port", "source.port"),
    ("Service", "application.protocoll"), #this is a wild guess. It's not guaranteed the field always exists in intelmq. The field "Service" is Mandatory!
    ("Domain", "source.fqdn") # optional
]



taxonomies = [
    # this x-arf map applies to intelmq-taxonomies
    "Fraud",
    "Intrusions", # Note: Not every intrusion is a "Fraud", the classification.type is Required!
    "Abusive Content",
]

types = [
    # this x-arf map applies to intelmq-types, those determine the Report-Type
    # xarf, intelmq
    ("defacement", "defacement"),
    ("phishing", "phishing"),
    ("spam", "spam"),
]

