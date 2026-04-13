from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, File, Form, UploadFile

from backend.modules.comparison.router import compare_documents
from backend.modules.summarization.router import download_docx, summarize_document

router = APIRouter(prefix="/api/modules", tags=["module-aliases"])


@router.post("/summarise/summarize")
async def module_summarise_summarize(
    file: Annotated[UploadFile, File(description="Document to summarize")],
    summary_type: Annotated[Literal["concise", "mid_level", "descriptive"], Form()] = "mid_level",
    page_range: Annotated[Optional[str], Form()] = None,
):
    return await summarize_document(file=file, summary_type=summary_type, page_range=page_range)


@router.get("/summarise/download/{task_id}")
def module_summarise_download(task_id: str):
    return download_docx(task_id)


@router.post("/compare/compare")
async def module_compare_compare(
    files: Annotated[List[UploadFile], File(description="Upload at least two documents to compare")],
    summary_type: Annotated[Literal["concise", "mid_level", "descriptive"], Form()] = "mid_level",
    prompt: Annotated[str, Form(description="Optional user comparison focus")] = "",
):
    return await compare_documents(files=files, summary_type=summary_type, prompt=prompt)
