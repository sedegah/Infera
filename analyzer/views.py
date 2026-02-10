import logging
import os
from uuid import uuid4

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import get_valid_filename

from .models import UploadedCode
from .services.code_parser import parse_codebase

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(settings.BASE_DIR, "uploaded_zips")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def upload_page(request):
    """
    Renders the upload HTML page.
    URL: /analyzer/upload/
    """
    return render(request, "analyzer/upload.html")


def analyze_page(request):
    """
    Renders the analysis HTML page.
    URL: /analyzer/analyze/
    """
    return render(request, "analyzer/analyze.html")


def _get_safe_upload_name(original_name: str) -> str:
    sanitized_name = get_valid_filename(original_name)
    if not sanitized_name:
        sanitized_name = "uploaded.zip"
    return f"{uuid4().hex}_{sanitized_name}"


@csrf_exempt
def upload_code(request: HttpRequest) -> JsonResponse:
    """
    Handles uploading a zip file of the codebase.
    Saves the file to disk and records it in the database.
    URL: /analyzer/api/upload/
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"}, status=405)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"status": "error", "message": "No file uploaded"}, status=400)

    if not uploaded_file.name.lower().endswith(".zip"):
        return JsonResponse({"status": "error", "message": "Only .zip files are supported"}, status=400)

    safe_name = _get_safe_upload_name(uploaded_file.name)

    try:
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(file_path, "wb+") as file_obj:
            for chunk in uploaded_file.chunks():
                file_obj.write(chunk)

        record = UploadedCode.objects.create(file_name=uploaded_file.name, file_path=file_path)

        return JsonResponse(
            {
                "status": "success",
                "file_id": record.id,
                "file_name": record.file_name,
            }
        )

    except Exception as exc:
        logger.error("Failed to upload file: %s", exc, exc_info=True)
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


@csrf_exempt
def analyze_code(request: HttpRequest) -> JsonResponse:
    """
    Analyzes the uploaded codebase for structure and optionally generates an ERD.
    URL: /analyzer/api/analyze/
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"}, status=405)

    file_id = request.POST.get("file_id")
    if not file_id:
        return JsonResponse({"status": "error", "message": "file_id is required"}, status=400)

    try:
        record = UploadedCode.objects.get(id=file_id)
    except UploadedCode.DoesNotExist:
        return JsonResponse({"status": "error", "message": "File not found"}, status=404)

    try:
        structure, erd_path = parse_codebase(record.file_path)
        return JsonResponse({"status": "success", "structure": structure, "erd_path": erd_path})
    except Exception as exc:
        logger.error("Failed to analyze codebase: %s", exc, exc_info=True)
        return JsonResponse(
            {
                "status": "error",
                "message": "Analysis failed",
                "details": str(exc),
            },
            status=500,
        )
