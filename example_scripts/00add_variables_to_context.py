import json


def create_notifications(context):
    # Read the substitutions from a file and add it to the context.
    # The Context is an Object which is available in all Mailgen-Scripts
    # and passed from script to script.
    js = {}
    with open('/etc/intelmq/mailgen/formats/variables.json', 'r') as j:
        js = json.load(j)

    substitution_variables = js.get("substitutions")

    # Determine the kind of Aggregation.
    aggregation = context.directive.aggregate_identifier
    asn_or_cidr = ""  # Can also be a CC
    if "source.asn" in aggregation:
        asn_or_cidr += "about AS %s" % aggregation["source.asn"]
    elif "cidr" in aggregation:
        asn_or_cidr = "about CIDR %s" % aggregation["cidr"]
    elif "source.geolocation.cc" in aggregation:
        asn_or_cidr = "about your Country %s" % aggregation["source.geolocation.cc"]

    substitution_variables["asn_or_cidr"] = asn_or_cidr

    context.substitutions = substitution_variables

    return None
