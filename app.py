import os
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

import translate

app = FastAPI(title="LifeGPT - AI Assistant for Financial Services")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(translate.router)


@app.on_event("startup")
async def startup_event():
    try:
        translate.load_models()
        translate.MODEL_LOAD_ERROR = None
    except Exception as e:
        translate.MODEL_LOAD_ERROR = str(e)
        print(f"Warning: translation model failed to load. Chat API will still run. Error: {translate.MODEL_LOAD_ERROR}")


@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open(os.path.join(BASE_DIR, "index.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>index.html not found. Please ensure it's in the same directory as app.py</h1>")


@app.get("/logo.jpg")
async def logo():
    logo_path = os.path.join(BASE_DIR, "logo.jpg")
    if not os.path.exists(logo_path):
        raise HTTPException(status_code=404, detail="logo.jpg not found")
    return FileResponse(logo_path, media_type="image/jpeg", filename="logo.jpg")


@app.post("/api/chat")
async def api_chat(payload: Dict):
    """Proxy chat requests to Azure OpenAI using credentials from .env."""
    messages = payload.get("messages", [])
    system = payload.get("system", "")
    model = payload.get("model")
    max_tokens = int(payload.get("max_tokens", 2000))
    attachments = payload.get("attachments", [])
    mode = payload.get("mode", "generic")

    query_text = ""
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            query_text = str(last_message.get("content") or "")

    attachment_context = translate.build_attachment_context(attachments, query_text=query_text, mode=mode)
    if attachment_context and messages:
        last_message = messages[-1]
        if isinstance(last_message, dict) and isinstance(last_message.get("content"), str):
            last_message = dict(last_message)
            last_message["content"] = f"{last_message['content']}{attachment_context}"
            messages = messages[:-1] + [last_message]

    guardrails = (
        "You are LifeGPT, a professional assistant for finance, insurance, regulations, and document analysis. "
        "Refuse any personal, informal, social, entertainment, or unrelated questions. "
        "Do not answer requests that are outside the active module. "
        "If the user asks for private information, credentials, account details, or other personal data, treat it as redacted and do not repeat it."
    )

    combined_system = f"{guardrails}\n\n{system}".strip()
    answer = translate.call_azure_openai_chat(messages, combined_system, model=model, max_tokens=max_tokens)
    return {"content": [{"text": answer}]}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": translate.text_model is not None,
        "model_load_error": translate.MODEL_LOAD_ERROR,
        "fonts_available": list(translate.FONTS.keys()),
        "poppler_path": translate.POPLLER_PATH,
        "device": str(translate.device) if translate.device else "not initialized",
    }


@app.get("/api/info")
async def api_info():
    return {
        "message": "PDF Translation API - Dual Pipeline",
        "model": "NLLB-200",
        "fonts_found": len(translate.FONTS),
        "pipelines": {
            "chat": {
                "endpoint": "/api/chat",
                "description": "General professional Q&A with document attachment support",
            },
            "regular": {
                "endpoint": "/translate-pdf/",
                "description": "For regular documents, brochures, articles",
                "method": "Text replacement",
            },
            "forms": {
                "endpoint": "/translate-form/",
                "description": "For proposal forms, applications, fillable PDFs",
                "method": "Label translation with field preservation",
            },
        },
        "utilities": {
            "analyze_form": "/analyze-form/",
            "health": "/health",
            "languages": "/languages",
            "translation_rules": "/translation-rules",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
