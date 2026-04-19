"""
Electional astrology forms for saved query creation and editing.
"""

from django import forms

from .models import SavedQuery


class SavedQueryForm(forms.ModelForm):
    """
    ModelForm for creating and editing SavedQuery instances.

    Uses inline location fields and JSON field for query parameters.
    """

    class Meta:
        model = SavedQuery
        fields = [
            "name",
            "query_type",
            "latitude",
            "longitude",
            "permission",
            "shared_with",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Wedding Date Selection",
                }
            ),
            "query_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "latitude": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "any",
                    "min": "-90",
                    "max": "90",
                    "placeholder": "e.g., 40.7128",
                }
            ),
            "longitude": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "any",
                    "min": "-180",
                    "max": "180",
                    "placeholder": "e.g., -74.0060",
                }
            ),
            "permission": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "shared_with": forms.SelectMultiple(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Model provides defaults for query_type, permission, latitude, and longitude,
        # so form fields are optional
        self.fields["query_type"].required = False
        self.fields["permission"].required = False
        self.fields["latitude"].required = False
        self.fields["longitude"].required = False
        # shared_with only required for NAMED_GROUP
        self.fields["shared_with"].required = False

    def clean(self):
        """Validate shared_with is only used with NAMED_GROUP permission."""
        cleaned_data = super().clean()
        permission = cleaned_data.get("permission")
        shared_with = cleaned_data.get("shared_with")

        if permission == SavedQuery.Permission.PRIVATE:
            # Clear shared_with for private sets
            cleaned_data["shared_with"] = []
        elif permission != SavedQuery.Permission.NAMED_GROUP:
            # Clear shared_with for non-named_group permissions
            cleaned_data["shared_with"] = []

        return cleaned_data


class SavedQueryCreateForm(SavedQueryForm):
    """
    Extended form for creating a new SavedQuery with automatic owner assignment.
    """

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.owner = self.user
        if commit:
            instance.save()
            # Handle M2M for shared_with
            if hasattr(self, "cleaned_data"):
                self.save_m2m()
        return instance
