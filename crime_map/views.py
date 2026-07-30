import csv
import io
import math

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CrimeFilterForm, CSVUploadForm, PredictionForm
from .models import CrimeData

# ---------------------------------------------------------------------------
# CSV import helpers
# ---------------------------------------------------------------------------

# Maps CSV column headers -> model field names. This makes the importer
# tolerant of the exact column ordering in the uploaded file.
COLUMN_MAP = {
    "incident_place": "incident_place",
    "incident_weekday": "incident_weekday",
    "part_of_the_day": "part_of_the_day",
    "latitude": "latitude",
    "longitude": "longitude",
    "crime_risk_score": "crime_risk_score",
    "murder_risk": "murder_risk",
    "rape_risk": "rape_risk",
    "kidnap_risk": "kidnap_risk",
    "bodyfound_risk": "bodyfound_risk",
    "robbery_risk": "robbery_risk",
    "assault_risk": "assault_risk",
    "total_crimes": "total_crimes",
    "total_murders": "total_murders",
    "total_rapes": "total_rapes",
    "total_kidnaps": "total_kidnaps",
    "total_bodyfounds": "total_bodyfounds",
    "total_robberys": "total_robberys",
    "total_assaults": "total_assaults",
    "risk_level": "risk_level",
    "marker_radius": "marker_radius",
    "dominant_crime": "dominant_crime",
}

INT_FIELDS = {
    "total_crimes",
    "total_murders",
    "total_rapes",
    "total_kidnaps",
    "total_bodyfounds",
    "total_robberys",
    "total_assaults",
}

FLOAT_FIELDS = {
    "latitude",
    "longitude",
    "crime_risk_score",
    "murder_risk",
    "rape_risk",
    "kidnap_risk",
    "bodyfound_risk",
    "robbery_risk",
    "assault_risk",
    "marker_radius",
}


def _coerce(field_name, raw_value):
    """Convert a raw CSV string into the proper Python type for the field."""
    if raw_value is None:
        return None
    value = raw_value.strip()
    if value == "":
        return 0 if field_name in INT_FIELDS or field_name in FLOAT_FIELDS else ""
    if field_name in INT_FIELDS:
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    if field_name in FLOAT_FIELDS:
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    return value


def import_csv_file(csv_file, replace_existing=False):
    """Parse an uploaded CSV file and create CrimeData records.

    Deduplication is performed by the natural key
    (incident_place, incident_weekday, part_of_the_day).  If a row with the
    same key already exists the existing record is updated instead of
    creating a duplicate.

    Returns the number of records successfully imported (new + updated).
    """
    decoded = csv_file.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded))

    # Normalise the header names so we can match them against COLUMN_MAP.
    original_fields = reader.fieldnames or []
    reader.fieldnames = [f.strip().lower().replace(" ", "_") for f in original_fields]

    if replace_existing:
        CrimeData.objects.all().delete()

    # Build a lookup of existing records keyed by (place, weekday, part_of_day)
    existing = {}
    if not replace_existing:
        for obj in CrimeData.objects.all():
            existing[(obj.incident_place, obj.incident_weekday, obj.part_of_the_day)] = obj

    records_to_create = []
    records_to_update = []

    for row in reader:
        kwargs = {}
        for csv_col, model_field in COLUMN_MAP.items():
            raw = row.get(csv_col)
            if raw is None:
                continue
            kwargs[model_field] = _coerce(model_field, raw)

        # Require at least a latitude/longitude to be useful on the map.
        if kwargs.get("latitude") is None or kwargs.get("longitude") is None:
            continue

        key = (
            kwargs.get("incident_place", ""),
            kwargs.get("incident_weekday", ""),
            kwargs.get("part_of_the_day", ""),
        )

        if key in existing:
            obj = existing[key]
            for field, value in kwargs.items():
                setattr(obj, field, value)
            records_to_update.append(obj)
        else:
            records_to_create.append(CrimeData(**kwargs))

    if records_to_create:
        CrimeData.objects.bulk_create(records_to_create, batch_size=500)
    if records_to_update:
        CrimeData.objects.bulk_update(
            records_to_update,
            [f for f in COLUMN_MAP.values() if f != "incident_place"],
            batch_size=500,
        )

    return len(records_to_create) + len(records_to_update)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def apply_filters(queryset, form):
    """Apply cleaned filter-form values to a CrimeData queryset."""
    if form.is_valid():
        cd = form.cleaned_data
        if cd.get("incident_place"):
            queryset = queryset.filter(incident_place__icontains=cd["incident_place"])
        if cd.get("risk_level"):
            queryset = queryset.filter(risk_level=cd["risk_level"])
        if cd.get("dominant_crime"):
            queryset = queryset.filter(dominant_crime=cd["dominant_crime"])
        if cd.get("incident_weekday"):
            queryset = queryset.filter(incident_weekday=cd["incident_weekday"])
        if cd.get("part_of_the_day"):
            queryset = queryset.filter(part_of_the_day=cd["part_of_the_day"])
        if cd.get("min_risk_score") is not None:
            queryset = queryset.filter(crime_risk_score__gte=cd["min_risk_score"])
    return queryset


@require_http_methods(["GET", "POST"])
def upload_csv(request):
    """Upload a CSV file and import its rows into the database."""
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            replace = form.cleaned_data.get("replace_existing", False)
            try:
                count = import_csv_file(csv_file, replace_existing=replace)
                messages.success(request, f"Successfully imported {count} record(s).")
            except Exception as exc:  # noqa: BLE001 - surface any parse error to user
                messages.error(request, f"Failed to import CSV: {exc}")
            return redirect("crime_map:upload_csv")
    else:
        form = CSVUploadForm()

    total_records = CrimeData.objects.count()
    return render(
        request,
        "crime_map/upload_csv.html",
        {"form": form, "total_records": total_records},
    )


def crime_map_view(request):
    """Render the Google Map with crime markers and filtering controls."""
    form = CrimeFilterForm(request.GET or None)
    queryset = CrimeData.objects.all()
    queryset = apply_filters(queryset, form)

    # Keep the payload reasonable: cap at 5000 markers for the page.
    points = queryset.values(
        "id",
        "incident_place",
        "incident_weekday",
        "part_of_the_day",
        "latitude",
        "longitude",
        "crime_risk_score",
        "risk_level",
        "marker_radius",
        "dominant_crime",
        "total_crimes",
        "total_murders",
        "total_rapes",
        "total_kidnaps",
        "total_bodyfounds",
        "total_robberys",
        "total_assaults",
    )[:5000]

    return render(
        request,
        "crime_map/map.html",
        {
            "form": form,
            "points": list(points),
            "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
            "shown_count": len(points),
            "total_count": CrimeData.objects.count(),
        },
    )


def crime_data_api(request):
    """JSON endpoint returning filtered crime points for dynamic map updates."""
    form = CrimeFilterForm(request.GET or None)
    queryset = CrimeData.objects.all()
    queryset = apply_filters(queryset, form)

    points = list(
        queryset.values(
            "id",
            "incident_place",
            "incident_weekday",
            "part_of_the_day",
            "latitude",
            "longitude",
            "crime_risk_score",
            "risk_level",
            "marker_radius",
            "dominant_crime",
            "total_crimes",
            "total_murders",
            "total_rapes",
            "total_kidnaps",
            "total_bodyfounds",
            "total_robberys",
            "total_assaults",
        )[:5000]
    )
    return JsonResponse({"points": points, "count": len(points)})


def dashboard(request):
    """Simple landing page with summary stats and links."""
    total = CrimeData.objects.count()
    by_risk = {
        level: CrimeData.objects.filter(risk_level=level).count()
        for level, _ in CrimeData.RISK_LEVELS
    }
    by_risk_pct = {}
    for level, _ in CrimeData.RISK_LEVELS:
        count = by_risk[level]
        by_risk_pct[level] = round((count / total * 100), 1) if total > 0 else 0.0
    return render(
        request,
        "crime_map/dashboard.html",
        {"total": total, "by_risk": by_risk, "by_risk_pct": by_risk_pct},
    )


# ---------------------------------------------------------------------------
# Crime prediction (pure-Python KNN)
# ---------------------------------------------------------------------------

def _haversine(lat1, lon1, lat2, lon2):
    """Return great-circle distance in kilometres between two points."""
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def predict_crime_risk(latitude, longitude, weekday, part_of_day, k=5):
    """Predict crime risk at a given location and time using KNN.

    Strategy:
      1. Filter records that match the requested weekday and part_of_day.
      2. If enough matches exist, use them; otherwise fall back to all records.
      3. Compute geographic distance to every candidate.
      4. Take the *k* nearest and compute an inverse-distance-weighted average
         of every risk field.
      5. Derive an overall risk level from the weighted crime_risk_score.

    Returns a dict with the prediction details.
    """
    all_records = list(
        CrimeData.objects.values(
            "latitude", "longitude", "crime_risk_score",
            "murder_risk", "rape_risk", "kidnap_risk",
            "bodyfound_risk", "robbery_risk", "assault_risk",
            "total_crimes", "total_murders", "total_rapes",
            "total_kidnaps", "total_bodyfounds", "total_robberys",
            "total_assaults", "risk_level", "dominant_crime",
            "incident_place", "incident_weekday", "part_of_the_day",
        )
    )

    if not all_records:
        return {
            "error": "No crime data available for prediction. Please upload a CSV first.",
            "predicted_risk_score": 0.0,
            "predicted_risk_level": "Very Low",
        }

    # Prefer records matching weekday + part_of_day
    candidates = [
        r for r in all_records
        if r["incident_weekday"] == weekday and r["part_of_the_day"] == part_of_day
    ]
    if len(candidates) < k:
        # Fall back to weekday-only matches
        candidates = [r for r in all_records if r["incident_weekday"] == weekday]
    if len(candidates) < k:
        # Fall back to all records
        candidates = all_records

    # Compute distances
    scored = []
    for r in candidates:
        dist = _haversine(latitude, longitude, r["latitude"], r["longitude"])
        scored.append((dist, r))

    # Sort by distance and take k nearest
    scored.sort(key=lambda x: x[0])
    nearest = scored[:k]

    # Inverse-distance weighting
    total_weight = 0.0
    weighted = {
        "crime_risk_score": 0.0,
        "murder_risk": 0.0,
        "rape_risk": 0.0,
        "kidnap_risk": 0.0,
        "bodyfound_risk": 0.0,
        "robbery_risk": 0.0,
        "assault_risk": 0.0,
        "total_crimes": 0.0,
        "total_murders": 0.0,
        "total_rapes": 0.0,
        "total_kidnaps": 0.0,
        "total_bodyfounds": 0.0,
        "total_robberys": 0.0,
        "total_assaults": 0.0,
    }

    for dist, r in nearest:
        # Avoid division by zero; use a small epsilon
        weight = 1.0 / (dist + 0.001)
        total_weight += weight
        for field in weighted:
            weighted[field] += r[field] * weight

    if total_weight > 0:
        for field in weighted:
            weighted[field] /= total_weight

    # Determine risk level from weighted crime_risk_score
    score = weighted["crime_risk_score"]
    if score >= 0.8:
        risk_level = "Very High"
    elif score >= 0.6:
        risk_level = "High"
    elif score >= 0.4:
        risk_level = "Moderate"
    elif score >= 0.2:
        risk_level = "Low"
    else:
        risk_level = "Very Low"

    # Determine dominant crime from weighted risks
    risk_fields = {
        "Murder": weighted["murder_risk"],
        "Rape": weighted["rape_risk"],
        "Kidnap": weighted["kidnap_risk"],
        "Body Found": weighted["bodyfound_risk"],
        "Robbery": weighted["robbery_risk"],
        "Assault": weighted["assault_risk"],
    }
    dominant_crime = max(risk_fields, key=risk_fields.get)

    # Nearest neighbor info for transparency
    nearest_info = [
        {
            "incident_place": r["incident_place"],
            "distance_km": round(dist, 2),
            "risk_level": r["risk_level"],
            "crime_risk_score": r["crime_risk_score"],
        }
        for dist, r in nearest
    ]

    return {
        "predicted_risk_score": round(score, 4),
        "predicted_risk_level": risk_level,
        "dominant_crime": dominant_crime,
        "nearest_neighbors": nearest_info,
        "weighted_risks": {k: round(v, 4) for k, v in weighted.items()},
        "total_crimes": round(weighted["total_crimes"], 1),
        "k_used": k,
        "candidates_considered": len(candidates),
    }


def predict_view(request):
    """Visitor-facing crime prediction form and results."""
    form = PredictionForm(request.GET or None)
    prediction = None
    if request.method == "GET" and request.GET:
        if form.is_valid():
            prediction = predict_crime_risk(
                latitude=form.cleaned_data["latitude"],
                longitude=form.cleaned_data["longitude"],
                weekday=form.cleaned_data["incident_weekday"],
                part_of_day=form.cleaned_data["part_of_the_day"],
                k=form.cleaned_data.get("k_neighbors", 5),
            )

    return render(
        request,
        "crime_map/predict.html",
        {
            "form": form,
            "prediction": prediction,
            "total_records": CrimeData.objects.count(),
        },
    )


def predict_api(request):
    """JSON API for crime prediction (for AJAX / external use)."""
    form = PredictionForm(request.GET or None)
    if not form.is_valid():
        return JsonResponse({"error": "Invalid parameters."}, status=400)

    prediction = predict_crime_risk(
        latitude=form.cleaned_data["latitude"],
        longitude=form.cleaned_data["longitude"],
        weekday=form.cleaned_data["incident_weekday"],
        part_of_day=form.cleaned_data["part_of_the_day"],
        k=form.cleaned_data.get("k_neighbors", 5),
    )
    return JsonResponse(prediction)
