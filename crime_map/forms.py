from django import forms

from .models import CrimeData


class CSVUploadForm(forms.Form):
    """Form for uploading a crime data CSV file."""

    csv_file = forms.FileField(
        label="CSV file",
        help_text="Upload a CSV with columns matching the crime dataset schema.",
    )
    replace_existing = forms.BooleanField(
        required=False,
        initial=False,
        label="Replace all existing records before import",
    )

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Please upload a .csv file.")
        return f


class CrimeFilterForm(forms.Form):
    """Filtering options for the map and data views."""

    RISK_CHOICES = [("", "All risk levels")] + list(CrimeData.RISK_LEVELS)
    CRIME_TYPES = [
        ("", "All crime types"),
        ("murder_risk", "Murder"),
        ("rape_risk", "Rape"),
        ("kidnap_risk", "Kidnap"),
        ("bodyfound_risk", "Body Found"),
        ("robbery_risk", "Robbery"),
        ("assault_risk", "Assault"),
    ]
    WEEKDAYS = [
        ("", "All days"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
        ("sunday", "Sunday"),
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
    ]
    PART_OF_DAY = [
        ("", "Any time"),
        ("morning", "Morning"),
        ("noon", "Noon"),
        ("afternoon", "Afternoon"),
        ("evening", "Evening"),
        ("night", "Night"),
    ]

    incident_place = forms.CharField(required=False)
    risk_level = forms.ChoiceField(choices=RISK_CHOICES, required=False)
    dominant_crime = forms.ChoiceField(choices=CRIME_TYPES, required=False)
    incident_weekday = forms.ChoiceField(choices=WEEKDAYS, required=False)
    part_of_the_day = forms.ChoiceField(choices=PART_OF_DAY, required=False)
    min_risk_score = forms.FloatField(required=False, min_value=0.0, max_value=1.0)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))


class CrimeDataForm(forms.ModelForm):
    """ModelForm for editing a single CrimeData record in the admin panel."""

    class Meta:
        model = CrimeData
        fields = [
            "incident_place",
            "incident_weekday",
            "part_of_the_day",
            "latitude",
            "longitude",
            "crime_risk_score",
            "murder_risk",
            "rape_risk",
            "kidnap_risk",
            "bodyfound_risk",
            "robbery_risk",
            "assault_risk",
            "total_crimes",
            "total_murders",
            "total_rapes",
            "total_kidnaps",
            "total_bodyfounds",
            "total_robberys",
            "total_assaults",
            "risk_level",
            "marker_radius",
            "dominant_crime",
        ]
        widgets = {
            "incident_place": forms.TextInput(attrs={"class": "form-control"}),
            "incident_weekday": forms.TextInput(attrs={"class": "form-control"}),
            "part_of_the_day": forms.TextInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "crime_risk_score": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
            "murder_risk": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
            "rape_risk": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
            "kidnap_risk": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
            "bodyfound_risk": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
            "robbery_risk": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
            "assault_risk": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
            "total_crimes": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_murders": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_rapes": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_kidnaps": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_bodyfounds": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_robberys": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_assaults": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "risk_level": forms.Select(attrs={"class": "form-control"}),
            "marker_radius": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "dominant_crime": forms.TextInput(attrs={"class": "form-control"}),
        }


class PredictionForm(forms.Form):
    """Form for visitors to predict crime risk at a location and time."""

    latitude = forms.FloatField(
        label="Latitude",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.0001", "placeholder": "e.g. 23.7089"}),
    )
    longitude = forms.FloatField(
        label="Longitude",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.0001", "placeholder": "e.g. 90.4125"}),
    )
    incident_weekday = forms.ChoiceField(
        label="Weekday",
        choices=CrimeFilterForm.WEEKDAYS,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    part_of_the_day = forms.ChoiceField(
        label="Time of day",
        choices=CrimeFilterForm.PART_OF_DAY,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    k_neighbors = forms.IntegerField(
        label="How many similar records to consider",
        initial=5,
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "20"}),
    )
