import os
from typing import Annotated, List, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.modules.translate import translate as translate_module
from backend.modules.summarization.document_parser import DocumentParser
from backend.modules.summarization.pii_masker import PIIMasker

router = APIRouter(prefix="/api/comparison", tags=["comparison"])

SUPPORTED_EXTENSIONS = {"txt", "csv", "xlsx", "xls", "pdf", "docx", "pptx", "msg"}
MAX_DOC_CHARS = int(os.getenv("COMPARISON_MAX_DOC_CHARS", "18000"))
MAX_COMPARE_FILES = int(os.getenv("COMPARISON_MAX_FILES", "5"))
MAX_COMPARISON_FILE_MB = int(os.getenv("COMPARISON_MAX_FILE_MB", "25"))

_parser = DocumentParser()
_masker = PIIMasker()


def _summary_instruction(level: str) -> str:
    level_map = {
        "concise": "Provide a compact comparison with key similarities and differences only.",
        "mid_level": "Provide a balanced comparison with thematic sections and evidence.",
        "descriptive": "Provide a detailed side-by-side comparison with all major points and caveats.",
    }
    return level_map.get(level, level_map["mid_level"])


@router.post("/compare")
async def compare_documents(
    files: Annotated[List[UploadFile], File(description="Upload at least two documents to compare")],
    summary_type: Annotated[Literal["concise", "mid_level", "descriptive"], Form()] = "mid_level",
    prompt: Annotated[str, Form(description="Optional user comparison focus")] = "",
):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Please upload at least 2 documents for comparison.")
    if len(files) > MAX_COMPARE_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files ({len(files)}). Max {MAX_COMPARE_FILES} documents are allowed.",
        )

    parsed_docs = []
    for upload in files:
        filename = upload.filename or "upload"
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type '.{ext}' for file '{filename}'.",
            )

        payload = await upload.read()
        if not payload:
            raise HTTPException(status_code=400, detail=f"Uploaded file '{filename}' is empty.")

        file_size_mb = len(payload) / (1024 * 1024)
        if file_size_mb > MAX_COMPARISON_FILE_MB:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File '{filename}' is too large ({file_size_mb:.1f}MB). "
                    f"Max {MAX_COMPARISON_FILE_MB}MB per file for comparison."
                ),
            )

        try:
            doc = _parser.parse(payload, filename)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse '{filename}': {exc}")

        parsed_docs.append(doc)

    compiled_context = []
    for idx, doc in enumerate(parsed_docs, start=1):
        masked_text = _masker.mask_text(doc.text)
        compact = masked_text[:MAX_DOC_CHARS]
        compiled_context.append(
            f"Document {idx}\n"
            f"File Type: {doc.file_type}\n"
            f"Total Pages: {doc.total_pages}\n"
            f"Content:\n{compact}\n"
        )

    user_focus = prompt.strip() or "Compare the uploaded documents across key themes, facts, risks, and inconsistencies."
    user_prompt = (
        f"{_summary_instruction(summary_type)}\n"
        "Return output with these sections:\n"
        "1. Executive Comparison\n"
        "2. Similarities\n"
        "3. Differences\n"
        "4. Risk / Conflict Areas\n"
        "5. Final Recommendation\n\n"
        "Formatting requirements:\n"
        "- Use clean Markdown headings and bullet points.\n"
        "- In section 'Differences', include at least one Markdown table.\n"
        "- The table must include one 'Aspect' column, one column per document (Document 1, Document 2, etc.), and a final 'Observation' column.\n"
        "- Keep entries concise and evidence-based from the provided documents only.\n\n"
        f"Comparison focus: {user_focus}\n\n"
        + "\n\n".join(compiled_context)
    )

    system_prompt = (
        "You are a professional document comparison assistant. "
        "Only use content present in provided documents. "
        "Do not invent facts. If details are missing, state that explicitly. "
        "Always return clean Markdown formatting with headings, bullets, readable spacing, "
        "and section dividers (---) for longer responses. Bold critical labels and use aligned "
        "Markdown tables for structured comparisons."
    )

    try:
        result = translate_module.call_azure_openai_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            model=None,
            max_tokens=2200,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Comparison generation failed: {exc}")

    # Best-effort restore of placeholders from the latest masking pass.
    result = _masker.unmask_text(result)

    return {
        "summary_type": summary_type,
        "documents_compared": len(parsed_docs),
        "comparison": result,
    }
