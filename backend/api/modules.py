from fastapi import APIRouter

router = APIRouter(prefix="/api/modules", tags=["module-docs"])

MODULES = {
    "generic": {
        "description": "General professional assistant chat.",
        "endpoint": "/api/modules/generic/chat",
    },
    "insurance": {
        "description": "Insurance-focused professional chat.",
        "endpoint": "/api/modules/insurance/chat",
    },
    "summarise": {
        "description": "Structured single-document summarization API.",
        "endpoint": "/api/modules/summarise/summarize",
    },
    "multidoc": {
        "description": "Multi-document Q&A chat powered by hybrid retrieval (QA engine).",
        "endpoint": "/api/modules/multidoc/chat",
    },
    "compare": {
        "description": "Multi-document comparison API.",
        "endpoint": "/api/modules/compare/compare",
    },
    "numbers": {
        "description": "Precision extraction and number-focused chat.",
        "endpoint": "/api/modules/numbers/chat",
    },
    "translate": {
        "description": "Document translation APIs.",
        "endpoint": "/api/modules/translate/upload",
    },
}


@router.get("")
def list_module_apis():
    return {
        "message": "LifeGPT module API catalog",
        "openapi_docs": "/docs",
        "redoc": "/redoc",
        "modules": MODULES,
    }
