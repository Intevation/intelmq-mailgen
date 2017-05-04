from intelmqmail.tableformat import build_table_format
import copy

def create_notifications(context):

    if context.directive["notification_format"] == "avalanche":

        # Copy Substitutions from the context to this script.
        # This way we can edit the variables in this script
        # without changing the context.
        substitution_variables = copy.copy(context.substitutions)


        data_format = context.directive["event_data_format"]
        # Prepare Message in CSV-Format
        formats = (
            ("source.asn", "ASN"),
            ("source.ip", "IP"),
            ("time.source", "Time"),
            ("classification.identifier", "Identifier"),
            ("malware.name", "Malware"),
            ("source.port", "Port"),
            ("destination.ip", "Destination-IP"),
            ("destination.port", "Destination-Port"),
            ("destination.fqdn", "Destination-FQDN"))

        form = build_table_format("avalanche", formats)

        if data_format == "avalanche_csv_inline":
            # If Inline-Messages are wanted
            substitution_variables["data_location_en"] = substitution_variables["data_location_inline_en"]
            substitution_variables["data_location_de"] = substitution_variables["data_location_inline_de"]
            return context.mail_format_as_csv(form,substitutions=substitution_variables)

        elif data_format == "avalanche_csv_attachment":
            # If Inline-Messages are wanted
            # TODO There is no attachment, yet!
            substitution_variables["data_location_en"] = substitution_variables["data_location_attached_en"]
            substitution_variables["data_location_de"] = substitution_variables["data_location_attached_de"]
            substitution_variables["data_inline_separator_en"] = ""
            substitution_variables["data_inline_separator_de"] = ""
            return context.mail_format_as_csv(form, substitutions=substitution_variables,
                                              attach_event_data=True)

    return None
