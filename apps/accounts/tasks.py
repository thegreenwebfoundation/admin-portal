from brevo_python import AddContactToList, ApiClient, Configuration, ContactsApi,CreateContact
from django.conf import settings
import dramatiq



@dramatiq.actor
def process_newsletter_registration(email : str):
    """
    Signs up the email to the Green Web Foundation mailing list,
    and adds the "source" tag in Brevo to identify that the user
    came from a admin portal signup.
    """
    configuration = Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api = ContactsApi(ApiClient(configuration))
    list_id = settings.BREVO_LIST_ID
    create_contact = CreateContact(email=email, attributes={"SOURCE": settings.BREVO_SOURCE})
    add_contact = AddContactToList(emails=[email])
    api.create_contact(create_contact)
    api.add_contact_to_list(list_id, add_contact)
