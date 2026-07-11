from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UsernameField

User = get_user_model()

class CustomUserCreationForm(forms.ModelForm):
    """
    A reimplementation the normal django UserCreationForm, but
    without the fields used for validating that passwords are
    the same.

    Used in the django admin, by internal staff.

    Validating passwords are the same isn't a responsibility
    of internal staff.
    That is left to the registration form used in
    the AdminRegistrationView, by users directly.
    """

    class Meta:
        model = User

        # we need at least one field defined in a ModelForm.
        # this is typically overridden in the containing
        # CustomUserAdmin
        fields = ("username",)

        # We use a special username field to normalise the submitted,
        # accounting for various text encodings in different locales
        field_classes = {"username": UsernameField}

    def save(self, commit=True):
        """
        Save the information for the given user, setting the
        password using the chosen encryption strategy specified
        in our settings file.
        """
        user = super().save(commit=False)

        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

