import io
import os
import uuid
from datetime import datetime
from typing import Annotated, Dict, Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openai import AzureOpenAI
from pydantic import BaseModel

from .document_parser import DocumentParser
from .docx_generator import generate_simple_summary_docx
from .pii_masker import PIIMasker
from .summarizer import DocumentSummarizer

AZURE_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://balic-gpt-contentgenerationnew.openai.azure.com",
)
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

SUPPORTED_EXTENSIONS = {"txt", "csv", "xlsx", "xls", "pdf", "docx", "pptx", "msg"}
MAX_SUMMARIZATION_FILE_MB = int(os.getenv("SUMMARIZATION_MAX_FILE_MB", "25"))
_docx_store: Dict[str, bytes] = {}

router = APIRouter(prefix="/api/summarization", tags=["summarization"])


def _make_azure_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
    )


_parser = DocumentParser()
_masker = PIIMasker()
_client = _make_azure_client()
_summarizer = DocumentSummarizer(_client, AZURE_DEPLOYMENT)


class SummarizeResponse(BaseModel):
    task_id: str
    filename: str
    file_type: str
    summary_type: str
    summary: str
    pii_detected: Dict[str, int]
    total_pages: int
    word_count: int
    generated_at: str
    download_url: str


@router.get("/health", tags=["summarization"])
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "supported_formats": sorted(SUPPORTED_EXTENSIONS),
    }


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_document(
    file: Annotated[UploadFile, File(description="Document to summarize")],
    summary_type: Annotated[
        Literal["concise", "mid_level", "descriptive"],
        Form(description="Level of summary detail"),
    ] = "mid_level",
    page_range: Annotated[
        Optional[str],
        Form(description="Page/slide range, e.g. '1-5' or '1,3,5'. Leave empty for all."),
    ] = None,
):
    filename = file.filename or "upload"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '.{ext}'. "
                f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > MAX_SUMMARIZATION_FILE_MB:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large ({file_size_mb:.1f}MB). "
                f"Max {MAX_SUMMARIZATION_FILE_MB}MB for summarization."
            ),
        )

    try:
        doc = _parser.parse(file_bytes, filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse document: {exc}")

    selected_text = _parser.get_content_by_range(doc, page_range or None)
    selected_images = _parser.get_images_by_range(doc, page_range or None)

    if not selected_text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the document.")

    masked_text = _masker.mask_text(selected_text)
    pii_report = _masker.get_pii_summary()

    try:
        masked_summary = _summarizer.generate_summary(
            text=masked_text,
            summary_type=summary_type,
            file_type=doc.file_type,
            metadata=doc.metadata,
            images=selected_images,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    final_summary = _masker.unmask_text(masked_summary)

    task_id = str(uuid.uuid4())
    try:
        docx_bytes = generate_simple_summary_docx(
            summary_text=final_summary,
            original_filename=filename,
            summary_type=summary_type,
        )
        _docx_store[task_id] = docx_bytes
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {exc}")

    return SummarizeResponse(
        task_id=task_id,
        filename=filename,
        file_type=doc.file_type,
        summary_type=summary_type,
        summary=final_summary,
        pii_detected=pii_report,
        total_pages=doc.total_pages,
        word_count=len(selected_text.split()),
        generated_at=datetime.utcnow().isoformat(),
        download_url=f"/api/summarization/download/{task_id}",
    )


@router.get(
    "/download/{task_id}",
    responses={
        200: {"content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}}},
        404: {"description": "Task not found or DOCX generation failed"},
    },
)
def download_docx(task_id: str):
    docx_bytes = _docx_store.get(task_id)
    if not docx_bytes:
        raise HTTPException(
            status_code=404,
            detail=f"No DOCX found for task_id '{task_id}'. It may have expired or generation failed.",
        )
    safe_name = f"summary_{task_id[:8]}.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
