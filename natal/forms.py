from django import forms

from .models import NatalSet, Place


class PlaceForm(forms.ModelForm):
    """
    ModelForm for creating and editing Place instances.
    """
    
    class Meta:
        model = Place
        fields = ["name", "latitude", "longitude", "timezone"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "City, Country or Location Name",
                }
            ),
            "latitude": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 40.7128",
                    "type": "number",
                    "step": "0.000001",
                }
            ),
            "longitude": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., -74.0060",
                    "type": "number",
                    "step": "0.000001",
                }
            ),
            "timezone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., America/New_York",
                }
            ),
        }
    
    def clean_latitude(self):
        """Validate latitude is within valid range."""
        lat = self.cleaned_data.get("latitude")
        if lat is not None:
            if lat < -90 or lat > 90:
                raise forms.ValidationError("Latitude must be between -90 and 90 degrees.")
        return lat
    
    def clean_longitude(self):
        """Validate longitude is within valid range."""
        lon = self.cleaned_data.get("longitude")
        if lon is not None:
            if lon < -180 or lon > 180:
                raise forms.ValidationError("Longitude must be between -180 and 180 degrees.")
        return lon


class PlaceCreateForm(PlaceForm):
    """
    Extended form for creating a new Place with automatic user assignment.
    """
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.created_by = self.user
        if commit:
            instance.save()
        return instance


class NatalSetForm(forms.ModelForm):
    """
    ModelForm for creating and editing NatalSet instances.
    """
    
    class Meta:
        model = NatalSet
        fields = [
            "name",
            "birth_datetime",
            "place",
            "notes",
            "permission",
            "shared_with",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., My Birth Chart",
                }
            ),
            "birth_datetime": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "place": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional notes about this natal chart...",
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
        
        # Filter place choices to user's places
        if self.user:
            self.fields["place"].queryset = Place.objects.filter(
                created_by=self.user
            )
        
        # Hide shared_with unless permission is NAMED_GROUP
        self.fields["shared_with"].required = False
    
    def clean(self):
        """Validate shared_with is only used with NAMED_GROUP permission."""
        cleaned_data = super().clean()
        permission = cleaned_data.get("permission")
        shared_with = cleaned_data.get("shared_with")
        
        if permission == NatalSet.Permission.PRIVATE:
            # Clear shared_with for private sets
            cleaned_data["shared_with"] = []
        elif permission != NatalSet.Permission.NAMED_GROUP:
            # Clear shared_with for non-named_group permissions
            cleaned_data["shared_with"] = []
        
        return cleaned_data


class NatalSetCreateForm(NatalSetForm):
    """
    Extended form for creating a new NatalSet with automatic owner assignment.
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
