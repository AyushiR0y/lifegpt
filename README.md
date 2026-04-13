# LifeGPT

LifeGPT is a FastAPI-based AI assistant for financial-services workflows.
It provides module-based chat, document summarization, multi-document comparison, PDF translation, and QA over multiple uploaded documents.

## Features

- Module-based chat API for:
  - generic
  - insurance
  - multidoc
  - numbers
  - translate
- Single-document summarization with downloadable DOCX output
- Multi-document comparison (2-5 files)
- PDF translation pipelines:
  - standard document translation
  - form-oriented translation
- Browser frontend served from the same app (`/`)
- Optional microphone input in frontend chat (browser Speech API)

## Tech Stack

- Backend: FastAPI, Uvicorn
- AI/LLM: Azure OpenAI, transformers/torch (optional local model path)
- Document processing: PyMuPDF, pdfplumber, pdf2image, Pillow, python-docx
- Frontend: HTML/CSS/Vanilla JavaScript

## Project Structure

- `app.py`: FastAPI app entrypoint, CORS setup, route wiring
- `backend/api/`: API routers (`/api/chat`, module routing, module catalog)
- `backend/modules/`: module implementations (translate, summarization, comparison, multidoc, etc.)
- `static/`: frontend assets
- `index.html`: frontend UI shell
- `FRONTEND_API_DOCUMENTATION.md`: frontend integration contract
- `RENDER_DEPLOYMENT.md`: Render deployment notes

## Requirements

- Python 3.10 (see `runtime.txt`)
- pip
- Poppler binaries available for PDF image workflows (already included in repo at `poppler-25.12.0/`)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the repository root.

Minimum for Azure-backed chat flows:

```env
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

Common optional settings:

```env
# CORS (comma-separated)
CORS_ALLOWED_ORIGINS=http://127.0.0.1:8000,http://localhost:3000
CORS_ALLOWED_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
CORS_ALLOWED_HEADERS=Authorization,Content-Type,X-Request-Id,X-Client-Version,Accept,Origin

# Translation upload limits (MB)
TRANSLATE_PDF_MAX_FILE_MB=50
TRANSLATE_FORM_MAX_FILE_MB=50

# Multidoc session behavior
MULTIDOC_SESSION_TTL_SECONDS=7200
MULTIDOC_MAX_SESSIONS=200

# Optional: skip loading large local models (recommended on low-memory hosts)
LIFEGPT_LOAD_LOCAL_MODELS=false
```

## Run Locally

Start the API server:

```bash
uvicorn app:app --reload --port 8000
```

Open the app:

- UI: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/health`

## API Overview

### Chat

- `POST /api/chat`
- `POST /api/modules/{module_name}/chat`

Supported `module_name` values: `generic`, `insurance`, `multidoc`, `numbers`, `translate`, `summarise`, `compare`.

### Summarization

- `POST /api/summarization/summarize`
- `GET /api/summarization/download/{task_id}`
- `GET /api/summarization/health`

### Comparison

- `POST /api/comparison/compare`

### Translation

- `POST /translate-pdf/`
- `POST /translate-form/`
- `GET /languages`
- `GET /translation-rules`
- `GET /test-rules`
- `GET /analyze-form/`

### Catalog

- `GET /api/modules`
- `GET /api/info`

For full request/response contracts, see `FRONTEND_API_DOCUMENTATION.md`.

## Frontend Notes

- The frontend sends module-based requests through `static/js/module-api-bridge.js`.
- Voice input uses `SpeechRecognition`/`webkitSpeechRecognition` when available.
- If voice input is unsupported in a browser, text input continues to work normally.

## Deploy on Render

The repo includes both `Procfile` and `render.yaml` for Render deployment.

High-level steps:

1. Create a new Render Web Service from this repository.
2. Set required Azure environment variables.
3. Ensure start command is:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

See `RENDER_DEPLOYMENT.md` for details and free-tier caveats.

## Notes

- Large local translation models can be memory-intensive; Azure-backed fallback is recommended for constrained environments.
- Keep module and endpoint usage aligned with `FRONTEND_API_DOCUMENTATION.md` for stable frontend integration.
