# Users and permissions
This page documents the topic of user accounts and their permissions.

## User accounts
Some parts of the systems maintained by Green Web Foundation are accessible to everyone - e.g. Green Web Dataset can be accessed by unauthenticated users.
However we do require a user account to access [Provider Portal](https://admin.thegreenwebfoundation.org/provider-portal/). Authenticated users (i.e. hosting providers) are able to submit verification requests in order to be included in the Green Web Database, and keep their submitted data up to date.

We require that each new account is activated by accessing a link sent to the email address given in the registration form. We do not allow inactive accounts to log in or perform any actions where authentication is required.

### Creating a user account
Users can create new accounts using the registration form: https://admin.thegreenwebfoundation.org/accounts/signup/

### Quirks 
Django User model [defines a flag called `is_staff`](https://docs.djangoproject.com/en/4.2/topics/auth/customizing/#django.contrib.auth.is_staff) to indicate users who are allowed to access the Admin panel. In the Green Web implementation we overwrite that logic and allow all authenticated users to access the Admin panel, thus making the `is_staff` flag irrelevant. You might still see this property existing in the User model, but it has no relevance and can be safely ignored.

## User permissions
Newly registered users are authorized to submit a new verification request and view the status of the submitted requests. In order to provide a granular control over who can perform which actions in the system, we have 2 levels of permission system available:
- user groups that define high-level authorization classes,
- object-level permissions that define access to a specific object.

### Groups

Currently the following groups exist in the system:
- `admin`: membership in this group indicates that the user has (almost) full access to Django Admin. Only Green Web Foundation staff members should belong to that group!
- `hostingprovider`: membership in this group allows to manage `Hostingprovider` objects via Django Admin.
- `datacenter`: membership in this group allows to manage `Datacenter` objects via Django Admin.

Under the hood we use default [Django Group mechanism](https://docs.djangoproject.com/en/4.2/topics/auth/default/#groups). You can think of them as labels/categories that are applied to users, and that don't have any meaning unless it's explicitly implemented in the system. One user can belong to multiple groups. See [`group_permissions.py`](https://github.com/thegreenwebfoundation/admin-portal/blob/master/apps/accounts/group_permissions.py) module to check out how we assign specific Django permissions to each group.

Please note that the use of `hostingprovider` and `datacenter` groups is mostly to support legacy approach of authorization, dating back to when Provider Portal or object-level permissions were not implemented. Most probably they could be decommissioned in favour of object-level permissions altogether. For now, we require that both of these groups are assigned to any user who's expected to make any changes to any `Hostingprovider` or `Datacenter` objects in the system. As a matter of fact, these groups are assigned automatically to each user upon registration.

Group membership can be managed by:
- users with `superuser` status,
- users who belong to the `admin` group.

### Object-level permissions
We need a way to attach specific users to existing `Hostingprovider` objects in the system to ensure that only authorized users are able to make updates to the data they submitted. This is enforced by object-level permission system, which implementation relies on the library [`django-guardian`](https://django-guardian.readthedocs.io/en/stable/).

Currently we have the following permissions defined:
- `manage_provider`: ties a specific user to a specific `Hostingprovider` object, 
- `manage_datacenter`: ties a specific user to a specific `Datacenter` object.

The mechanism provided by `django-guardian` allows us to add arbitrary number of permissions. For example:
- a single user can manage multiple providers/datacenters,
- a single provider/datacenter can be managed by multiple users.

Various parts of the system (Provider Portal, API views and Admin views) will inspect the object-level permission to determine whether the authenticated users is authorized to view/edit given object. As an example: if user `alice` wants to upload new evidence to the existing hosting provider `Green Provider`, the system will check the rule: does the permission `manage_provider` exist for user `alice` and object `Green Provider`? The same mechanism is used in places where we list all providers attached to a given user, e.g. Provider Portal (retrieve all objects for which `alice` has the permission `manage_provider`). And same for places where we list all users attached to a given provider, e.g. Django Admin page for `Green Provider` will retrieve all users who have the permission `manage_provider` for the object `Green Provider`.

The mechanism provided by `django-guardian` can be extended to groups, too. Currently we use it to assign a global permission (meaning: to all objects in the system) for the `admin` group. As a consequence, all `admin` group members have access to all hosting providers and all datacenters. Given that there are thousands of providers in our Green Web Database, listing all of them in the Provider Portal for `admin` group members could be cumbersome (potential performance issues) and not useful (the rendered list will take ages to scroll through). That's why wherever we list all objects for a given user (see `alice` example above), we ignore global permissions and those that are connected to group membership, leaving only explicit user-object permissions. To illustrate that let's extend the example above:
- user `alice` from the example above belongs to the `admin` group, 
- there are 5000 hosting provider objects in the database,
- there exists only 1 explicit permission `manage_provider` for `alice`: that is to `Green Provider`.

Even though `alice` as a member of the `admin` group can manage all 5000 providers, when she visits the Provider Portal she will only see `Green Provider` listed. 

The object-level permissions can be managed in the Django Admin by users who belong to the `admin` group. In order to add/edit permissions:
- log in to the Django Admin,
- open the detail page of a specific `Hostingprovider`/`Datacenter` object, e.g. `https://admin.thegreenwebfoundation.org/admin/accounts/hostingprovider/1/change/` for a provider with ID=1,
- click on the `Permissions` button in the top right corner,
- choose an existing permission to edit or select a user to create a new permission.
