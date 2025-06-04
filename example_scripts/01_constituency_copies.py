import types

bcc_contacts = {
    'Government': [{'recipients': ['internal-gov@cert.example'], 'format': 'CSV_inline'}],
    'Energy': [{'recipients': ['internal-energy@cert.example'], 'format': 'CSV_attachment'}],
}


def mail_format_as_csv_bcc(self, *args, **kwargs):
    notifications = self.old_mail_format_as_csv(*args, **kwargs)
    ticket_number = notifications[0].ticket

    recipient_group = self.directive.aggregate_identifier.get('recipient_group')
    self.logger.debug(f'Recipient group {recipient_group} detected.')
    if recipient_group and recipient_group in bcc_contacts:
        for bcc_contact in bcc_contacts[recipient_group]:
            self.logger.debug(f"Sending email in bcc to {bcc_contact['recipients']} with format {bcc_contact['format']}'")
            notifications.extend(self.old_mail_format_as_csv(*args, **kwargs,
                                                             envelope_tos=bcc_contact['recipients'],
                                                             attach_event_data=bcc_contact['format'] == 'CSV_attachment',
                                                             ticket_number=ticket_number,
                                                             mark_as_sent=False))
    return notifications


def create_notifications(context):
    # Replace the mail_format_as_csv method of the context
    context.old_mail_format_as_csv = context.mail_format_as_csv
    context.mail_format_as_csv = types.MethodType(mail_format_as_csv_bcc, context)

    return None
