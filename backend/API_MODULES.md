# LifeGPT Module APIs

This project now exposes module-first APIs for all functional modules.

## Live API Documentation
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- Module Catalog JSON: `/api/modules`

## Module Endpoints

### Generic
- `POST /api/modules/generic/chat`
- Purpose: Professional general-purpose responses.

### Insurance
- `POST /api/modules/insurance/chat`
- Purpose: Insurance-focused responses.

### Summarisation
- `POST /api/summarization/summarize`
- `GET /api/summarization/download/{task_id}`
- `GET /api/summarization/health`
- Purpose: Upload a document and generate summary output.

### Multi-Doc Q&A
- `POST /api/modules/multidoc/chat`
- Purpose: Question answering across uploaded document context using QA-style hybrid retrieval.

### Comparison
- `POST /api/comparison/compare`
- Purpose: Compare two or more documents with structured output.

### Number Accuracy
- `POST /api/modules/numbers/chat`
- Purpose: Number extraction and numeric precision tasks.

### Translation
- `POST /translate-pdf/`
- `POST /translate-form/`
- Purpose: Document translation pipelines.

## Backward-Compatible Endpoint
- `POST /api/chat`
- Generic chat endpoint that accepts `mode` in payload.
