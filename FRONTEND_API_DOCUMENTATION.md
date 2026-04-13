# Frontend API Integration Contract

This document defines the frontend handoff contract for integrating with the LifeGPT API.

## 1. Scope

- Audience: frontend developers integrating web or mobile clients.
- Purpose: request/response contracts, headers, endpoint usage, and error handling.
- Excluded: backend architecture notes, internal implementation details, and roadmap decisions.

## 2. Base URL, Versioning, and Transport

- Local base URL: http://127.0.0.1:8000
- Browser deployment base URL: same origin as hosting app (preferred).
- API versioning: current routes are unversioned. Use the canonical routes below as the v1 integration baseline.
- Content types by family:
  - Chat endpoints: application/json
  - Summarization/comparison endpoints: multipart/form-data
  - Translation upload/form endpoints: multipart/form-data request, application/pdf response

## 3. Authentication and Required Headers

Frontend contract for all protected environments:

- Authorization: Bearer <token>
- Chat JSON endpoints: Content-Type: application/json
- Multipart endpoints: do not set Content-Type manually; let FormData set boundary

Recommended common headers:

- X-Request-Id: <uuid>
- X-Client-Version: <app-version>

## 4. Canonical Endpoint Matrix

Use only these endpoints for new frontend integration.

| Frontend mode | Canonical endpoint | Method | Request body | Response shape |
|---|---|---|---|---|
| generic | /api/modules/generic/chat | POST | JSON | { content: [{ text }] } |
| insurance | /api/modules/insurance/chat | POST | JSON | { content: [{ text }] } |
| multidoc | /api/modules/multidoc/chat | POST | JSON | { content: [{ text }] } |
| numbers | /api/modules/numbers/chat | POST | JSON | { content: [{ text }] } |
| translate (chat) | /api/modules/translate/chat | POST | JSON | { content: [{ text }] } |
| summarise | /api/summarization/summarize | POST | multipart/form-data | top-level object with summary |
| compare | /api/comparison/compare | POST | multipart/form-data | top-level object with comparison |
| translate (file) | /translate-pdf/ | POST | multipart/form-data | binary PDF stream |
| translate (form) | /translate-form/ | POST | multipart/form-data | binary PDF stream |

Legacy aliases may exist for backward compatibility, but do not use them for new clients.

## 5. Response Parsing Rules

Parser logic must be endpoint-family aware:

- Chat family: read content array and join content[i].text
- Summarization family: read summary from top-level response body
- Comparison family: read comparison from top-level response body
- Translation upload/form family: treat response as binary PDF stream

Recommended parser switch:

- chatParser for /api/chat and /api/modules/{module}/chat
- summarizeParser for /api/summarization/summarize
- compareParser for /api/comparison/compare
- fileStreamParser for /translate-pdf/ and /translate-form/

## 6. JSON Chat Contract

Endpoints:

- POST /api/chat
- POST /api/modules/{module_name}/chat

Allowed module names:

- generic, insurance, multidoc, numbers, translate, summarise, compare

Request example:

```json
{
  "max_tokens": 2000,
  "chat_id": "chat_1713000000000_ab12cd",
  "messages": [
    { "role": "user", "content": "User question" }
  ],
  "attachments": [
    {
      "name": "doc1.txt",
      "type": "text/plain",
      "content": {
        "raw": "...",
        "isBase64": false
      }
    }
  ],
  "mode": "generic",
  "summary_depth": "balanced"
}
```

chat_id usage:

- Required for Multi-Doc continuity across turns.
- Optional for other modes.

Response example:

```json
{
  "content": [
    { "text": "Assistant response text" }
  ]
}
```

Status codes:

- 200 success
- 404 unknown module
- 500 server error

404 example:

```json
{
  "detail": "Unknown module: abc"
}
```

## 7. Summarization Contract

Endpoint:

- POST /api/summarization/summarize

Form fields:

- file (required)
- summary_type (optional): concise | mid_level | descriptive
- page_range (optional): examples 1-5, 1,3,5

Server limit:

- Max file size: 25 MB per summarize request (default)

Frontend mapping requirement:

- concise -> concise
- balanced -> mid_level
- detailed -> descriptive

Response example:

```json
{
  "task_id": "uuid",
  "filename": "policy.pdf",
  "file_type": "pdf",
  "summary_type": "mid_level",
  "summary": "Generated summary...",
  "pii_detected": { "email": 1 },
  "total_pages": 10,
  "word_count": 2400,
  "generated_at": "2025-01-01T12:00:00",
  "download_url": "/api/summarization/download/{task_id}"
}
```

Status codes:

- 200 success
- 400 empty upload
- 413 file too large
- 415 unsupported extension
- 422 parse failure / no text extracted
- 500 DOCX generation failure
- 502 upstream LLM failure

## 8. Comparison Contract

Endpoint:

- POST /api/comparison/compare

Form fields:

- files (required, repeatable): minimum 2, maximum 5 (enforced)
- summary_type (optional): concise | mid_level | descriptive
- prompt (optional): comparison focus

Server limits:

- Max files per request: 5
- Max file size: 25 MB per file (default)

Response example:

```json
{
  "summary_type": "mid_level",
  "documents_compared": 2,
  "comparison": "Structured comparison output..."
}
```

Status codes:

- 200 success
- 400 fewer than 2 files / too many files / empty file
- 413 one or more files exceed size limit
- 415 unsupported extension
- 422 parse failure
- 502 comparison generation failure

## 9. Translation Contract

### 9.1 Upload Translation

Endpoint:

- POST /translate-pdf/

Form fields:

- file (required, pdf)
- source_lang (optional, default English)
- target_lang (required)
- dpi (optional, default 200)
- client_id (optional)

Server limit:

- Max file size: 50 MB per request (default)

Request example (multipart fields):

- file = policy.pdf
- source_lang = English
- target_lang = Hindi
- dpi = 200
- client_id = chat_1713000000000_ab12cd

Success response:

- HTTP 200
- Content-Type: application/pdf
- Body: translated PDF file stream

Status codes:

- 200 success
- 400 invalid file type
- 413 file too large
- 500 translation pipeline failure

### 9.2 Form Translation

Endpoint:

- POST /translate-form/

Form fields:

- file (required, pdf)
- source_lang (required)
- target_lang (required)
- dpi (optional, default 150)
- max_pages (optional, default 30)
- client_id (optional)

Server limits:

- Max file size: 50 MB per request (default)
- max_pages default 30 for request processing

Request example (multipart fields):

- file = form.pdf
- source_lang = English
- target_lang = Marathi
- dpi = 150
- max_pages = 30
- client_id = chat_1713000000000_ab12cd

Success response:

- HTTP 200
- Content-Type: application/pdf
- Body: translated form PDF stream

Status codes:

- 200 success
- 400 invalid file type
- 413 file too large
- 500 translation pipeline failure

### 9.3 Translation Utilities

- GET /languages
- GET /translation-rules
- GET /test-rules
- GET /analyze-form/

## 10. WebSocket Progress Contract

Endpoint:

- WS /ws/{client_id}

Current message format:

- Server emits plain text frames.

Observed examples:

- Processing PDF: policy.pdf
- Translation: English -> Hindi
- Page 1/5: OCR...
- Page 1/5: Done
- Translation complete!
- Error: <reason>

Frontend handling requirements:

- Render each frame as a log line.
- Treat lines starting with Error: as failure state.
- Treat line containing complete as completion signal.

## 11. Attachment Object Shape (Chat JSON)

```json
{
  "name": "file.pdf",
  "type": "application/pdf",
  "size": 12345,
  "content": {
    "raw": "data:application/pdf;base64,...",
    "isBase64": true
  }
}
```

Bridge handling:

- Multipart endpoints: convert attachment content to Blob/File and append to FormData.
- JSON endpoints: forward as attachments array.

## 12. Error Contract

Standard error body:

```json
{
  "detail": "Human-readable error message"
}
```

Frontend fallback order:

- detail
- error.message
- generic HTTP status fallback

## 13. Limits, Timeout, and CORS Integration Notes

Frontend-enforced limits (recommended):

- Chat attachment uploads: max 10 MB per file

Server-enforced limits:

- /api/summarization/summarize: 25 MB max file size (default), returns HTTP 413 when exceeded
- /api/comparison/compare: max 5 files and 25 MB max per file (default), returns HTTP 400 for too many files and HTTP 413 for oversize files
- /translate-pdf/: 50 MB max file size (default), returns HTTP 413 when exceeded
- /translate-form/: 50 MB max file size (default), returns HTTP 413 when exceeded

Client timeout guidance (recommended):

- Chat/summarize/compare calls: 120 seconds
- Translation upload/form calls: 300 seconds

CORS integration requirement:

- Prefer same-origin frontend + API deployment.
- If cross-origin is required, backend must explicitly allow the frontend origin.

Recommended backend CORS configuration for cross-origin browser clients:

- CORS_ALLOWED_ORIGINS=http://localhost:5173,https://app.example.com
- CORS_ALLOW_CREDENTIALS=true
- CORS_ALLOWED_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
- CORS_ALLOWED_HEADERS=Authorization,Content-Type,X-Request-Id,X-Client-Version,Accept,Origin
- CORS_EXPOSE_HEADERS=Content-Disposition

Important browser rule:

- Do not use wildcard origin (*) with credentials enabled. Browsers reject this combination.

## 14. Discovery and Health Endpoints

- GET /api/modules
- GET /api/info
- GET /health
- GET /api/summarization/health

## 15. Frontend Integration Checklist

- Use canonical endpoints from Section 4 only.
- Always send Authorization: Bearer <token> in protected environments.
- Implement parser branching by endpoint family exactly as in Section 5.
- Map summary_depth balanced to summary_type mid_level before summarize/compare calls.
- Send translation requests as FormData and parse response as PDF binary stream.
- Handle websocket progress lines as plain text and map Error: lines to failure UI.
- Surface detail from API errors directly in user-safe error messages.
