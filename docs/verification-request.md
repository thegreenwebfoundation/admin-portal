# Verification request
This page documents the design decision and implementation details of the verification request.

## What is a verification request?
It's a multi-step form allowing green hosting providers to onboard their organisations' data to be available in the Green Web Foundation dataset.

## How to access the verification request form?
It's not publicly available yet: it's only available for selected users,
based on a feature flag called `provider_request` that is [managed in the admin panel](https://admin.thegreenwebfoundation.org/admin/waffle/flag/2/change/).

Authenticated users that have the flag enabled can access the following pages:
- `/requests/new/` to start a new verification request,
- `/requests/` to view all submitted requests.

## How is the form implemented?
In the implementation of the verification request form we use a complex stack of different libraries and components:
- native Django [`Form`s](https://docs.djangoproject.com/en/4.1/ref/forms/api/) and [`FormSet`s](https://docs.djangoproject.com/en/4.1/topics/forms/formsets/),
- []`SessionWizard` from `django-formtools`](https://github.com/jazzband/django-formtools) to implement a multi-step form in a single view,
- [`MultiForm`s from `django-betterforms`](https://django-betterforms.readthedocs.io/en/latest/multiform.html) to represent multiple forms in a single form-like container (so that it can be used as a single step of the form wizard),
- [`ConvenientFormset` from `django-convenient-formset`](https://github.com/tiesjan/django-convenient-formsets) to implement a dynamic formset that allows adding and deleting forms,
- the widget [`ResubmitFileWidget` from `django-file-resubmit`](https://github.com/un1t/django-file-resubmit) to work around an issue with disappearing files ([see more details below](#working-with-file-upload-in-the-form)).

## Working with `WizardView`
We are using [`WizardView`](https://django-formtools.readthedocs.io/en/latest/wizard.html#creating-a-wizardview-subclass) from the library [`django-formtools`](https://django-formtools.readthedocs.io/) to display a single form per page, over multiple pages. The consecutive forms of the wizard are validated when each step is submitted.

The use of [`SessionWizardView`](https://django-formtools.readthedocs.io/en/latest/wizard.html#formtools.wizard.views.SessionWizardView) makes it convenient for keeping the in-progress forms in a database-backed user sessions. No data loss should occur as long as the user keeps the session cookie in their browser (and as long as their session remains valid).

The final step of the wizard is a preview: all submitted data can be reviewed one last time before submitting the whole verification request.

Upon submitting the final step, the data is persisted as a `ProviderRequest` object (and related objects).

## Quirks of Django forms
This section documents "gotchas" and weird behaviors, as well as chosen workarounds, related to Django forms and the libraries that are used to implement the verification request form.

### Working with file upload in the form
Workaround implemented [in this PR](https://github.com/thegreenwebfoundation/admin-portal/pull/422).

On one of the steps of the wizard we request the user to upload files that will serve as evidence of being a green provider. After uploading a file, when user navigates forwards in the wizard and then decides to come back to the upload step, the files appear to be gone. This is because - for security reasons - the file input cannot have a default value. 

Another issue related to this was that upon raising a `ValidationError` on any of the forms in this step, even if the offending form doesn't contain a file, all files would disappear.

The solution to both of these cases was to use a custom file widget from the library [`django-file-resubmit`](https://github.com/un1t/django-file-resubmit), which not only retains the file in cache in case of the `ValidationError`, but also displays the name of the uploaded file next to the file input.

### Working with error messages
Form and fields validation: [see the documentation here](https://docs.djangoproject.com/en/4.1/ref/forms/validation/).

It's worth noting that [Django Formsets contain additional errors](https://docs.djangoproject.com/en/4.1/topics/forms/formsets/#error-messages) that are returned by `non_form_errors()`, similarly to how Forms contain `non_field_errors()`. The templates that are used to render formsets must either explicitly output these values or the errors needs to be propagated to the `errors` property.

See the corresponding workaround [in this PR](https://github.com/thegreenwebfoundation/admin-portal/pull/419).

## Preview implementation details
The preview step is configured to display a `PreviewForm`: a form that does not contain any data or validation logic. When the `WizardView` renders the `PreviewForm` in a template, all cleaned data from the previous steps is injected to the template context. This way we are able to render the already submitted and validated data, without running validation on it again.


## How do I test the multistep form?

There are two ways you can test the form wizard forms - with integration tests that use the database, and with more focussed unit tests that just test step in a form wizard by itself.

### Testing the form wizard end to end

You can test an end to end form submission by POSTing the form wizard, with the corresponding payload for each subsequent form in the multi-step wizard.

```python
    # assume each dict in this list is a valid submission with the correct step named
    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ]
    client.force_login(user)

    # when: a multi step submission has been successfully completed
    for step, data in enumerate(form_data, 1):
        response = client.post(urls.reverse("provider_registration"), data, follow=True)
```

In this case here, you need to make sure that the correct step name is in each form payload. So for `wizard_form_org_details_data`, where there is a single form, you need to pass the correct step number, and match the field names.

```python
    wizard_form_org_details_data =  {
        "provider_registration_view-current_step": "0",
        "0-name": " ".join(faker.words(5)),
        "0-website": faker.url(),
        "0-description": faker.sentence(10),
        "0-authorised_by_org": "True",
    }
```

For complicated formsets, you need to pass in the extra information a formset expects to see, AND key it to the correct step number. Here's an example for step 4 of the `provider_registration_view` form wizard, where we are sending network data. Note that we need to use the correct step number in the form payload


```python
@pytest.fixture()
def wizard_form_network_data(sorted_ips):
    """
    Returns valid data for step NETWORK_FOOTPRINT of the wizard
    as expected by the POST request.
    """
    return {
        "provider_registration_view-current_step": "4",
        "ips__4-TOTAL_FORMS": "2",
        "ips__4-INITIAL_FORMS": "0",
        "ips__4-0-start": sorted_ips[0],
        "ips__4-0-end": sorted_ips[1],
        "ips__4-1-start": sorted_ips[2],
        "ips__4-1-end": sorted_ips[3],
        "asns__4-TOTAL_FORMS": "1",
        "asns__4-INITIAL_FORMS": "0",
        "asns__4-0-asn": faker.random_int(min=100, max=999),
    }

```

### Testing focussed steps of the form wizard

End to end tests require the database to be set up, which can be time consuming. You can use focussed unit tests to test the same form, without needing to run through the slow and computationally expensive steps by testing just a specific step in a wizard.

When doing this, you no longer need to explicitly name the step in a wizard you are making a submission for, as this form might be used outside the original context of the multi-step form wizard.



```python
@pytest.fixture()
def wizard_form_network_data(sorted_ips):
    """
    Returns valid data for step NETWORK_FOOTPRINT of the wizard
    as expected by the POST request.
    """
    return {

        "ips-TOTAL_FORMS": "2",
        "ips-INITIAL_FORMS": "0",
        "ips-0-start": sorted_ips[0],
        "ips-0-end": sorted_ips[1],
        "ips-1-start": sorted_ips[2],
        "ips-1-end": sorted_ips[3],

        "asns-TOTAL_FORMS": "1",
        "asns-INITIAL_FORMS": "0",
        "asns-0-asn": faker.random_int(min=100, max=999),
    }
```

You would then test a form submission the normal way, without hitting the database.

```python
def test_network_form_in_isolation(wizard_form_network_data):
    multiform = NetworkFootprintForm(wizard_form_network_data)
    assert multiform.is_valid()
```
