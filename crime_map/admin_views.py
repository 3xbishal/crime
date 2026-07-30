"""Custom admin panel views (NOT Django's built-in admin).

Provides:
  * Login / logout authentication
  * Dashboard with summary statistics
  * CSV upload with automatic deduplication
  * Data listing, detail, edit, delete
  * CSV export
  * PDF report export
  * Upload history
"""

import csv
import io
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.views.decorators.http import require_http_methods

from .forms import CSVUploadForm, CrimeDataForm, CrimeFilterForm
from .models import CrimeData, CSVUpload

# Re-use the column-mapping helpers from views.py
from .views import COLUMN_MAP, INT_FIELDS, FLOAT_FIELDS, _coerce

try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------

def admin_login(request):
    """Render a simple login form and authenticate staff users."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_panel:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect("admin_panel:dashboard")
        messages.error(request, "Invalid credentials or you do not have admin access.")

    return render(request, "admin_panel/login.html")


@login_required(login_url="admin_panel:login")
def admin_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("admin_panel:login")


def admin_required(view_func):
    """Decorator: require an authenticated staff user."""
    return login_required(
        user_passes_test(lambda u: u.is_staff)(view_func),
        login_url="admin_panel:login",
    )


# ---------------------------------------------------------------------------
# CSV import with deduplication
# ---------------------------------------------------------------------------

def import_csv_with_dedup(csv_file, replace_existing=False):
    """Parse an uploaded CSV and import rows, deduplicating by natural key.

    The natural key is (incident_place, incident_weekday, part_of_the_day).
    If a row with the same key already exists, the existing record is updated
    with the new values instead of creating a duplicate.

    Returns a dict with counts: imported, updated, skipped.
    """
    decoded = csv_file.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded))

    # Normalise header names
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
    skipped = 0

    for row in reader:
        kwargs = {}
        for csv_col, model_field in COLUMN_MAP.items():
            raw = row.get(csv_col)
            if raw is None:
                continue
            kwargs[model_field] = _coerce(model_field, raw)

        # Require at least latitude/longitude
        if kwargs.get("latitude") is None or kwargs.get("longitude") is None:
            skipped += 1
            continue

        key = (
            kwargs.get("incident_place", ""),
            kwargs.get("incident_weekday", ""),
            kwargs.get("part_of_the_day", ""),
        )

        if key in existing:
            # Update existing record
            obj = existing[key]
            for field, value in kwargs.items():
                setattr(obj, field, value)
            records_to_update.append(obj)
        else:
            records_to_create.append(CrimeData(**kwargs))

    # Bulk operations
    if records_to_create:
        CrimeData.objects.bulk_create(records_to_create, batch_size=500)
    if records_to_update:
        CrimeData.objects.bulk_update(
            records_to_update,
            [f for f in COLUMN_MAP.values() if f != "incident_place"],
            batch_size=500,
        )

    return {
        "imported": len(records_to_create),
        "updated": len(records_to_update),
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_required
def admin_dashboard(request):
    """Admin dashboard with summary statistics."""
    total = CrimeData.objects.count()
    by_risk = {
        level: CrimeData.objects.filter(risk_level=level).count()
        for level, _ in CrimeData.RISK_LEVELS
    }
    by_weekday = {}
    for wd in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        by_weekday[wd] = CrimeData.objects.filter(incident_weekday=wd).count()
    by_part = {}
    for pt in ["morning", "noon", "afternoon", "evening", "night"]:
        by_part[pt] = CrimeData.objects.filter(part_of_the_day=pt).count()

    top_places = (
        CrimeData.objects.values("incident_place")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    recent_uploads = CSVUpload.objects.order_by("-uploaded_at")[:5]

    return render(request, "admin_panel/dashboard.html", {
        "total": total,
        "by_risk": by_risk,
        "by_weekday": by_weekday,
        "by_part": by_part,
        "top_places": top_places,
        "recent_uploads": recent_uploads,
    })


# ---------------------------------------------------------------------------
# CSV Upload
# ---------------------------------------------------------------------------

@admin_required
@require_http_methods(["GET", "POST"])
def admin_upload_csv(request):
    """Upload a CSV file with automatic deduplication."""
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            replace = form.cleaned_data.get("replace_existing", False)
            try:
                with transaction.atomic():
                    result = import_csv_with_dedup(csv_file, replace_existing=replace)
                    CSVUpload.objects.create(
                        file=csv_file,
                        records_imported=result["imported"],
                        records_skipped=result["skipped"],
                        records_updated=result["updated"],
                    )
                total_msg = (
                    f"Imported {result['imported']} new, "
                    f"updated {result['updated']} existing, "
                    f"skipped {result['skipped']} invalid row(s)."
                )
                messages.success(request, total_msg)
            except Exception as exc:
                messages.error(request, f"Failed to import CSV: {exc}")
            return redirect("admin_panel:upload_csv")
    else:
        form = CSVUploadForm()

    total_records = CrimeData.objects.count()
    return render(request, "admin_panel/upload_csv.html", {
        "form": form,
        "total_records": total_records,
    })


# ---------------------------------------------------------------------------
# Data management
# ---------------------------------------------------------------------------

@admin_required
def admin_data_list(request):
    """List all crime records with optional filtering."""
    qs = CrimeData.objects.all()
    place = request.GET.get("place", "")
    risk = request.GET.get("risk", "")
    weekday = request.GET.get("weekday", "")
    part = request.GET.get("part", "")

    if place:
        qs = qs.filter(incident_place__icontains=place)
    if risk:
        qs = qs.filter(risk_level=risk)
    if weekday:
        qs = qs.filter(incident_weekday=weekday)
    if part:
        qs = qs.filter(part_of_the_day=part)

    qs = qs.order_by("-uploaded_at", "incident_place")
    # Paginate
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "admin_panel/data_list.html", {
        "records": page_obj,
        "place": place,
        "risk": risk,
        "weekday": weekday,
        "part": part,
        "WEEKDAYS": CrimeFilterForm.WEEKDAYS,
        "PART_OF_DAY": CrimeFilterForm.PART_OF_DAY,
    })


@admin_required
def admin_data_detail(request, pk):
    """Show details of a single crime record."""
    record = get_object_or_404(CrimeData, pk=pk)
    return render(request, "admin_panel/data_detail.html", {"record": record})


@admin_required
@require_http_methods(["GET", "POST"])
def admin_data_edit(request, pk):
    """Edit a single crime record."""
    record = get_object_or_404(CrimeData, pk=pk)
    if request.method == "POST":
        form = CrimeDataForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Record updated successfully.")
            return redirect("admin_panel:data_detail", pk=pk)
    else:
        form = CrimeDataForm(instance=record)
    return render(request, "admin_panel/data_edit.html", {"form": form, "record": record})


@admin_required
@require_http_methods(["GET", "POST"])
def admin_data_delete(request, pk):
    """Delete a single crime record."""
    record = get_object_or_404(CrimeData, pk=pk)
    if request.method == "POST":
        record.delete()
        messages.success(request, "Record deleted.")
        return redirect("admin_panel:data_list")
    return render(request, "admin_panel/data_delete.html", {"record": record})


@admin_required
def admin_data_export(request):
    """Export all (or filtered) crime records as CSV."""
    qs = CrimeData.objects.all()
    place = request.GET.get("place", "")
    risk = request.GET.get("risk", "")
    weekday = request.GET.get("weekday", "")
    part = request.GET.get("part", "")

    if place:
        qs = qs.filter(incident_place__icontains=place)
    if risk:
        qs = qs.filter(risk_level=risk)
    if weekday:
        qs = qs.filter(incident_weekday=weekday)
    if part:
        qs = qs.filter(part_of_the_day=part)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="crime_data_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        "incident_place", "incident_weekday", "part_of_the_day",
        "latitude", "longitude", "crime_risk_score",
        "murder_risk", "rape_risk", "kidnap_risk", "bodyfound_risk",
        "robbery_risk", "assault_risk",
        "total_crimes", "total_murders", "total_rapes", "total_kidnaps",
        "total_bodyfounds", "total_robberys", "total_assaults",
        "risk_level", "marker_radius", "dominant_crime",
    ])
    for obj in qs:
        writer.writerow([
            obj.incident_place, obj.incident_weekday, obj.part_of_the_day,
            obj.latitude, obj.longitude, obj.crime_risk_score,
            obj.murder_risk, obj.rape_risk, obj.kidnap_risk, obj.bodyfound_risk,
            obj.robbery_risk, obj.assault_risk,
            obj.total_crimes, obj.total_murders, obj.total_rapes, obj.total_kidnaps,
            obj.total_bodyfounds, obj.total_robberys, obj.total_assaults,
            obj.risk_level, obj.marker_radius, obj.dominant_crime,
        ])

    return response


@admin_required
def admin_data_export_pdf(request):
    """Export filtered crime records as a PDF report."""
    if pisa is None:
        messages.error(request, "PDF export is not available. Please install xhtml2pdf.")
        return redirect("admin_panel:data_list")

    qs = CrimeData.objects.all()
    place = request.GET.get("place", "")
    risk = request.GET.get("risk", "")
    weekday = request.GET.get("weekday", "")
    part = request.GET.get("part", "")

    if place:
        qs = qs.filter(incident_place__icontains=place)
    if risk:
        qs = qs.filter(risk_level=risk)
    if weekday:
        qs = qs.filter(incident_weekday=weekday)
    if part:
        qs = qs.filter(part_of_the_day=part)

    qs = qs.order_by("-uploaded_at", "incident_place")
    records = list(qs[:500])

    by_risk = {}
    for level, _ in CrimeData.RISK_LEVELS:
        by_risk[level] = qs.filter(risk_level=level).count()

    total = qs.count()
    now = datetime.now()

    template = get_template("admin_panel/report_pdf.html")
    html = template.render({
        "records": records,
        "total": total,
        "by_risk": by_risk,
        "place": place,
        "risk": risk,
        "weekday": weekday,
        "part": part,
        "generated_at": now,
        "request": request,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="crime_report_{now.strftime("%Y%m%d_%H%M%S")}.pdf"'
    )
    pisa.CreatePDF(html, dest=response)
    return response


@admin_required
def admin_upload_list(request):
    """List all CSV upload history."""
    uploads = CSVUpload.objects.order_by("-uploaded_at")
    return render(request, "admin_panel/upload_list.html", {"uploads": uploads})
