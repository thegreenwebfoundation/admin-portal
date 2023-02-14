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
We are using [`WizardView`](https://django-formtools.readthedocs.io/en/latest/wizard.html#creating-a-wizardview-subclass) from the library [`django-formtools`](https://django-formtools.readthedocs.io/) to display a single form per page, over multiple pages. The consecutive forms of the wizard are validated when each step is submitted.

The use of [`SessionWizardView`](https://django-formtools.readthedocs.io/en/latest/wizard.html#formtools.wizard.views.SessionWizardView) makes it convenient for keeping the in-progress forms in a database-backed user sessions. No data loss should occur as long as the user keeps the session cookie in their browser (and as long as their session remains valid).

The final step of the wizard is a preview: all submitted data can be reviewed one last time before submitting the whole verification request.

Upon submitting the final step, the data is persisted as a `ProviderRequest` object (and related objects).

## Preview implementation details
The preview step is configured to display a `PreviewForm`: a form that does not contain any data or validation logic. When the `WizardView` renders the `PreviewForm` in a template, all cleaned data from the previous steps is injected to the template context. This way we are able to render the already submitted and validated data, without running validation on it again.
