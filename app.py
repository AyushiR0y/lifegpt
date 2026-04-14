import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.modules.translate import translate as translate_module
from backend.api.chat import router as chat_router
from backend.api.module_aliases import router as module_aliases_router
from backend.api.modules import router as modules_catalog_router
from backend.modules.comparison import router as comparison_router
from backend.modules.summarization import router as summarization_router

app = FastAPI(title="LifeGPT - AI Assistant for Financial Services")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _parse_csv_env(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


default_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

cors_allowed_origins = _parse_csv_env(os.getenv("CORS_ALLOWED_ORIGINS", "")) or default_cors_origins
cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").strip().lower() in {"1", "true", "yes", "on"}
cors_allowed_methods = _parse_csv_env(os.getenv("CORS_ALLOWED_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS"))
cors_allowed_headers = _parse_csv_env(
    os.getenv(
        "CORS_ALLOWED_HEADERS",
        "Authorization,Content-Type,X-Request-Id,X-Client-Version,Accept,Origin",
    )
)
cors_expose_headers = _parse_csv_env(os.getenv("CORS_EXPOSE_HEADERS", "Content-Disposition"))
cors_max_age = int(os.getenv("CORS_MAX_AGE", "600"))
cors_origin_regex = os.getenv("CORS_ALLOWED_ORIGIN_REGEX", "").strip() or None

if cors_allow_credentials and "*" in cors_allowed_origins:
    raise RuntimeError("Invalid CORS configuration: allow_credentials=true cannot be used with wildcard origins.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allowed_methods,
    allow_headers=cors_allowed_headers,
    expose_headers=cors_expose_headers,
    max_age=cors_max_age,
)

app.include_router(translate_module.router)
app.include_router(chat_router)
app.include_router(module_aliases_router)
app.include_router(modules_catalog_router)
app.include_router(summarization_router)
app.include_router(comparison_router)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


def should_load_local_models() -> bool:
    """Decide whether to load large local translation models at startup.

    Override with LIFEGPT_LOAD_LOCAL_MODELS=true/false.
    On Render, default to False to avoid OOM on free tier.
    """
    override = os.getenv("LIFEGPT_LOAD_LOCAL_MODELS")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}

    on_render = os.getenv("RENDER", "").strip().lower() in {"1", "true", "yes", "on"}
    has_hosted_port = bool(os.getenv("PORT"))
    return not (on_render or has_hosted_port)


@app.on_event("startup")
async def startup_event():
    if not should_load_local_models():
        translate_module.MODEL_LOAD_ERROR = "Local model loading skipped by configuration"
        print("Skipping local translation model load (using Azure fallback).")
        return

    try:
        translate_module.load_models()
        translate_module.MODEL_LOAD_ERROR = None
    except Exception as e:
        translate_module.MODEL_LOAD_ERROR = str(e)
        print(f"Warning: translation model failed to load. Chat API will still run. Error: {translate_module.MODEL_LOAD_ERROR}")


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


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": translate_module.text_model is not None,
        "model_load_error": translate_module.MODEL_LOAD_ERROR,
        "fonts_available": list(translate_module.FONTS.keys()),
        "poppler_path": translate_module.POPLLER_PATH,
        "device": str(translate_module.device) if translate_module.device else "not initialized",
    }


@app.get("/api/info")
async def api_info():
    return {
        "message": "PDF Translation API - Dual Pipeline",
        "model": "NLLB-200",
        "fonts_found": len(translate_module.FONTS),
        "pipelines": {
            "chat": {
                "endpoint": "/api/chat",
                "description": "General professional Q&A with document attachment support",
            },
            "module_chat": {
                "endpoint": "/api/modules/{module_name}/chat",
                "description": "Module-wise chat endpoints for generic/insurance/multidoc/numbers/translate",
            },
            "summarization": {
                "endpoint": "/api/modules/summarise/summarize",
                "description": "Upload a document and generate concise/mid_level/descriptive summaries",
            },
            "comparison": {
                "endpoint": "/api/modules/compare/compare",
                "description": "Upload 2+ documents and generate a structured comparison report",
            },
            "regular": {
                "endpoint": "/api/modules/translate/upload",
                "description": "For regular documents, brochures, articles",
                "method": "Text replacement",
            },
            "forms": {
                "endpoint": "/api/modules/translate/form",
                "description": "For proposal forms, applications, fillable PDFs",
                "method": "Label translation with field preservation",
            },
        },
        "utilities": {
            "analyze_form": "/analyze-form/",
            "health": "/health",
            "languages": "/languages",
            "translation_rules": "/translation-rules",
            "module_catalog": "/api/modules",
            "swagger": "/docs",
            "redoc": "/redoc",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
