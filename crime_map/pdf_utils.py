"""Shared helpers for generating PDF reports with xhtml2pdf.

On cPanel shared hosting, ``xhtml2pdf`` / ``reportlab`` can fail silently or
raise exceptions that are not clearly surfaced.  This module centralises PDF
rendering so the real cause can be logged (see ``logs/django.log``) and a
friendly error can be returned to the browser instead of a bare 500.
"""

import logging

from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template

logger = logging.getLogger(__name__)

try:
    from xhtml2pdf import pisa
    HAS_PISA = True
except ImportError:
    pisa = None
    HAS_PISA = False


def render_pdf_response(request, template_name, context, filename):
    """Render a Django template to a PDF attachment response.

    Returns an ``HttpResponse`` with the PDF bytes on success, or ``None``
    on failure (after logging the error and queuing an error message).
    """
    if not HAS_PISA:
        logger.error("xhtml2pdf is not installed on this server.")
        messages.error(
            request,
            "PDF export is not available because xhtml2pdf is not installed. "
            "Please run: pip install xhtml2pdf==0.2.16",
        )
        return None

    try:
        template = get_template(template_name)
        html = template.render(context)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        result = pisa.CreatePDF(html, dest=response, encoding="UTF-8")

        if result.err:
            logger.error("xhtml2pdf reported errors while generating %s", filename)
            messages.error(
                request,
                "PDF generation failed on the server. Please check the server "
                "logs (logs/django.log) for details.",
            )
            return None

        return response
    except Exception as exc:  # noqa: BLE001 - surface any server error
        logger.exception("PDF generation failed for %s: %s", filename, exc)
        messages.error(
            request,
            "PDF generation failed on the server. Please check the server "
            "logs (logs/django.log) for details.",
        )
        return None