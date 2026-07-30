from django.db import models


class CrimeData(models.Model):
    """Stores a single crime-risk record imported from a CSV upload."""

    RISK_LEVELS = [
        ("Very Low", "Very Low"),
        ("Low", "Low"),
        ("Moderate", "Moderate"),
        ("High", "High"),
        ("Very High", "Very High"),
    ]

    incident_place = models.CharField(max_length=200, db_index=True)
    incident_weekday = models.CharField(max_length=20, db_index=True)
    part_of_the_day = models.CharField(max_length=20, db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    crime_risk_score = models.FloatField(default=0.0)
    murder_risk = models.FloatField(default=0.0)
    rape_risk = models.FloatField(default=0.0)
    kidnap_risk = models.FloatField(default=0.0)
    bodyfound_risk = models.FloatField(default=0.0)
    robbery_risk = models.FloatField(default=0.0)
    assault_risk = models.FloatField(default=0.0)

    total_crimes = models.IntegerField(default=0)
    total_murders = models.IntegerField(default=0)
    total_rapes = models.IntegerField(default=0)
    total_kidnaps = models.IntegerField(default=0)
    total_bodyfounds = models.IntegerField(default=0)
    total_robberys = models.IntegerField(default=0)
    total_assaults = models.IntegerField(default=0)

    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default="Very Low", db_index=True)
    marker_radius = models.FloatField(default=7.0)
    dominant_crime = models.CharField(max_length=50, default="")

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "incident_place"]
        # A single record is uniquely identified by place + weekday + time-of-day.
        # This is the natural key used for deduplication during CSV import.
        unique_together = ("incident_place", "incident_weekday", "part_of_the_day")
        indexes = [
            models.Index(fields=["risk_level"]),
            models.Index(fields=["incident_place", "risk_level"]),
        ]

    def __str__(self):
        return f"{self.incident_place} - {self.incident_weekday} {self.part_of_the_day} ({self.risk_level})"


class CSVUpload(models.Model):
    """Tracks the CSV files that have been uploaded for import."""

    file = models.FileField(upload_to="csv_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    records_imported = models.IntegerField(default=0)
    records_skipped = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.file.name} ({self.uploaded_at:%Y-%m-%d %H:%M})"
