# M1 DocTriage Pipeline — Walkthrough

## What Was Built

Three new files implementing the complete M1 document upload & extraction pipeline:

| File | Purpose |
|------|---------|
| [pdf_service.py](file:///c:/Users/antop/OneDrive/Desktop/blahblah/backend/services/pdf_service.py) | PDF processing: hash computation, blank/encrypted checks, PyPDF2 text extraction, page-to-image conversion |
| [m1_doctriage.py](file:///c:/Users/antop/OneDrive/Desktop/blahblah/backend/modules/m1_doctriage.py) | Core 4-tier pipeline + LLM extraction + structured input (Path B) |
| [upload.py](file:///c:/Users/antop/OneDrive/Desktop/blahblah/backend/routes/upload.py) | `POST /upload-document` (PDF) and `POST /upload-structured` (JSON) endpoints |

## Pipeline Flow

```mermaid
graph TD
    A["Upload PDF"] --> B["Tier 1: Metadata Gate"]
    B -->|"duplicate/blank/encrypted"| R["REJECT"]
    B -->|"pass"| C["Tier 2: PyPDF2 Text Extract"]
    C -->|"> 50 chars"| E["LLM Extraction (Gemini)"]
    C -->|"no text"| D["Tier 3: Tesseract OCR"]
    D -->|"confidence ≥ 85%"| E
    D -->|"low confidence"| F["Tier 4: Cloud OCR (placeholder)"]
    F --> E
    E --> G["ClaimSchema JSON"]

    H["Structured JSON Input"] --> G
```

## Verification Results

| Test | Result |
|------|--------|
| `pip install -r requirements.txt` | ✅ All dependencies installed |
| Server startup (`python main.py`) | ✅ `routes.upload` router loaded |
| `GET /health` | ✅ Returns `{"status": "healthy"}` |
| `POST /api/upload-structured` | ✅ Returns proper [ClaimSchema](file:///c:/Users/antop/OneDrive/Desktop/blahblah/backend/models/claim_schema.py#104-126) with auto-generated [claim_id](file:///c:/Users/antop/OneDrive/Desktop/blahblah/backend/modules/m1_doctriage.py#70-75) |
| `POST /api/upload-document` (PDF) | ⏳ Needs Gemini API key in `.env` to test |

## Next Step

To test PDF upload with LLM extraction, create `backend/.env`:
```
GEMINI_API_KEY=your-key-here
```
