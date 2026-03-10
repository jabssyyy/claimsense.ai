# ClaimSense.ai — MVP Build Brief
### Full context for any developer or AI assistant starting fresh on this project.
### Read this completely before writing a single line of code.

---

## WHAT IS THIS PROJECT

ClaimSense.ai is a medical insurance claims processing system built for the Indian market.
It is being built as an MVP

Theme: FinTech and Insurance.

---

## THE PROBLEM THIS SOLVES

17% of medical insurance claims in India are rejected for avoidable administrative
reasons - wrong codes, missing documents, policy rules nobody checked before submission.
Each rejection means the insurer reviews the same claim twice. The patient waits.
The hospital waits. Everyone pays for a mistake that could have been caught beforehand.

ClaimSense.ai catches everything before the claim is submitted. Not after rejection.

---

## MVP SCOPE

The MVP covers three modules plus document-level fraud detection.
M4 (Fraud Graph Network) and M5 (Zero Wait Discharge) remain out of scope
for the hackathon build. They exist in the full design but will be demoed
with pre-cached outputs, not live code.

**In scope:**
- M1 - DocTriage Pipeline (document upload, extraction, and fraud detection)
- M2 - Policy Rules Engine (coverage validation)
- M3 - Clean Claim Guarantee (final quality check and submission package)
- Document Fraud Detection (integrated into M1 via Gemini Vision)

---

## TECH STACK

| Layer | Technology |
|---|---|
| Frontend | React (simple, clean UI) |
| Backend | Python FastAPI |
| LLM | Gemini API (Google AI Studio) |
| OCR Tier 3 | Tesseract (local, free) |
| OCR Tier 4 | Gemini Vision API (uses existing Gemini key) |
| PDF to Image | Poppler + pdf2image |
| Fraud Detection | Gemini Vision API (document tampering analysis) |
| Database | PostgreSQL |
| Storage | Local file storage for demo |

**Important:** All LLM calls must go through a single abstraction function so switching
from Gemini to another model is one line change. Never hardcode direct Gemini calls
scattered across the codebase.

```python
# All LLM calls go through these abstraction functions
def call_llm(prompt: str, system: str = "") -> str:
    # Text-only LLM call. Swap Gemini for any other model here.
    pass

def call_llm_vision(prompt: str, images: list[bytes], system: str = "") -> str:
    # Multimodal LLM call for OCR and fraud detection on page images.
    pass

def call_llm_json(prompt, system) -> dict:    # Text -> parsed JSON
def call_llm_vision_json(prompt, images, system) -> dict:  # Vision -> parsed JSON
```

---

## FOLDER STRUCTURE

```
claimsense-ai/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # API keys, settings
│   ├── models/
│   │   └── claim_schema.py      # The standard claim JSON schema
│   ├── modules/
│   │   ├── m1_doctriage.py      # M1 logic
│   │   ├── m2_policy_engine.py  # M2 logic
│   │   └── m3_clean_claim.py    # M3 logic
│   ├── services/
│   │   ├── llm_service.py       # Single LLM abstraction function
│   │   ├── ocr_service.py       # Tesseract + Gemini Vision OCR
│   │   ├── pdf_service.py       # PyPDF2 text extraction
│   │   └── encryption_service.py # AES/Fernet PII field encryption
│   ├── routes/
│   │   ├── upload.py            # POST /upload-document
│   │   ├── validate.py          # POST /validate-policy
│   │   └── submit.py            # POST /submit-claim
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── UploadPage.jsx       # Step 1: Upload documents
│   │   │   ├── ExtractionPage.jsx   # Step 2: Show extracted JSON
│   │   │   ├── ValidationPage.jsx   # Step 3: Policy validation results
│   │   │   └── SubmissionPage.jsx   # Step 4: Final submission package
│   │   └── components/
│   │       ├── ClaimCard.jsx
│   │       ├── StatusBadge.jsx
│   │       └── DocumentUploader.jsx
│   └── package.json
└── README.md
```

---

## THE STANDARD CLAIM JSON SCHEMA

This is the single most important thing in the entire codebase.
M1 produces this. M2 and M3 consume it. Every module speaks this language.
Do not change field names without updating all three modules.

```json
{
  "claim_id": "CLM-2026-001",
  "input_type": "PDF | Structured",
  "patient": {
    "name": "Rahul Sharma",
    "dob": "1985-06-15",
    "gender": "Male",
    "abha_id": "12-3456-7890-1234",
    "phone": "9876543210",
    "email": "rahul@email.com",
    "policy_number": "POL-AH-4421"
  },
  "hospital": {
    "hospital_id": "HSP-1001",
    "name": "Apollo Hospitals",
    "doctor_name": "Dr. Meera Iyer",
    "department": "Cardiology",
    "staff_name": "Admin Staff",
    "tpa_name": "Medi Assist"
  },
  "admission": {
    "admission_date": "2026-02-10",
    "discharge_date": "2026-02-14",
    "admission_type": "Emergency",
    "ward_type": "ICU",
    "room_type": "Single",
    "length_of_stay": 4
  },
  "medical": {
    "primary_diagnosis": "Hypertension",
    "icd10_code": "I10",
    "secondary_diagnosis": "",
    "secondary_icd10": "",
    "procedure": "Angioplasty",
    "procedure_code": "PROC-2001"
  },
  "billing": {
    "room_charges": 12000,
    "icu_charges": 8000,
    "doctor_fees": 15000,
    "ot_charges": 5000,
    "medicines": 6000,
    "lab_charges": 4000,
    "other_charges": 0,
    "total_bill": 50000,
    "pre_auth_amount": 45000
  },
  "documents": {
    "hospital_bill": true,
    "discharge_summary": true,
    "prescription": false,
    "lab_reports": true,
    "pre_auth_letter": true,
    "id_proof": false
  },
  "insurance": {
    "insurer_name": "Star Health",
    "pre_auth_number": "PA-2026-5521"
  },
  "meta": {
    "status": "Submitted",
    "submitted_at": "2026-02-15T10:30:00Z"
  }
}
```

---

## MODULE 1 — DocTriage Pipeline

### What it does
Reads uploaded documents and converts them into the standard claim JSON above.

### Two input paths
**Path A - PDF Upload:** Patient or hospital uploads a PDF bill, discharge summary,
prescription, or lab report. M1 reads it and extracts all claim fields.

**Path B - Structured Input:** Hospital sends data directly in JSON or form format.
M1 just parses it into the standard schema. No OCR needed.

Both paths produce the exact same claim JSON output.

### Four processing tiers (PDF path only)

**Tier 1 - Metadata Gate**
Before any processing, check:
- Is the file a duplicate? (hash check)
- Is the file blank or corrupted?
- Is the file password protected?
If any of these are true, reject immediately. Cost: near zero.

**Tier 2 - Text Layer Detection**
If the PDF was created digitally (not scanned), it has an embedded text layer.
Use PyPDF2 or pdfplumber to extract text directly. Fast and free.
Resolves approximately 60-70% of documents at this tier.
No OCR needed.

**Tier 3 - Standard OCR**
For scanned documents. Use Tesseract OCR locally.
Tesseract gives a confidence score per field.
If confidence above 85% - accept.
If confidence below 85% - escalate to Tier 4.

**Tier 4 - Gemini Vision OCR**
Uses the Gemini Vision API (same API key as text extraction, no extra cost).
Handles handwriting, low quality scans, regional Indian language text.
Only approximately 20% of documents reach this tier.
Returns high-confidence extraction (0.92) for content Tesseract cannot read.

### Document Fraud Detection (integrated into M1)
After text extraction, M1 runs a parallel fraud detection pass using Gemini Vision.
Page images are sent with a forensic analysis prompt that checks for:
- Edited or replaced text (font/size inconsistencies)
- Digital manipulation artifacts (cut-paste, clone stamps)
- Altered monetary amounts or dates
- Inconsistent document formatting
- Mismatched signatures or stamps

Returns a fraud assessment alongside the extracted claim:
```json
{
  "risk_level": "low | medium | high",
  "risk_score": 0.05,
  "findings": [],
  "summary": "The document appears genuine with no signs of tampering."
}
```

**Non-blocking design:** Fraud detection failures never stop the pipeline.
If Gemini Vision is unavailable or errors, processing continues normally
with fraud_detection as null in the response.

### Output
Structured claim JSON record plus fraud detection results. Claim moves to M2.

### API Endpoint
```
POST /upload-document
Content-Type: multipart/form-data
Body: file (PDF or image)
Response: { success, claim, fraud_detection, extraction_text_length }
```

---

## MODULE 2 — Policy Rules Engine

### What it does
Reads the insurance policy document and validates whether the claim qualifies
for coverage. Uses deterministic Python logic for all coverage decisions.
Never uses AI for the actual pass/fail decision - only for reading the policy
and writing the summary.

### Why deterministic logic and not AI for validation
AI can hallucinate. A coverage decision that is wrong cannot be explained to
a regulator or a patient. Fixed Python if-else logic gives the same answer
every time and is fully auditable.

### Three steps

**Step 1 - Policy Parsing (LLM)**
Send the policy PDF to Gemini once.
Gemini reads all the rules and outputs them as a structured JSON cache.
This cache is saved and reused for all future claims under the same policy.
The LLM is called ONCE per policy, not once per claim.

Example policy rules JSON:
```json
{
  "policy_id": "POL-AH-4421",
  "insurer": "Star Health",
  "room_rent_limit_per_day": 5000,
  "waiting_period_days": 30,
  "exclusions": ["dental", "cosmetic surgery", "maternity"],
  "copay_percentage": 10,
  "sub_limits": {
    "icu": 10000,
    "ot": 8000
  },
  "cashless_eligible": true,
  "reimbursement_eligible": true,
  "pre_auth_required": true
}
```

**Step 2 - Deterministic Rules Validation (Pure Python)**
Run the claim JSON against the policy rules JSON using if-else logic.
Check each rule one by one:
- Room rent: is claim room charge within daily limit?
- Waiting period: has the patient held the policy long enough?
- Exclusions: is the procedure on the exclusion list?
- Co-pay: calculate patient liability vs insurer liability
- Sub-limits: are ICU, OT charges within sub-limits?
- Pre-auth: was pre-authorization obtained?

Each check returns PASS, FAIL, or WARNING with a specific reason.

**Step 3 - Coverage Summary Generation (LLM)**
Send the validation results to Gemini.
Gemini writes a plain English summary explaining:
- What is covered
- What is denied and exactly why
- What the patient owes vs what the insurer owes
- What documents are still missing

### Outputs
If validation fails: "Incomplete Claim" with specific reasons. User is notified.
If validation passes: "Validated Claim" moves to M3.

### API Endpoint
```
POST /validate-policy
Body: { claim_json, policy_pdf (base64) }
Response: { validation_results, coverage_summary, validated_claim_json }
```

---

## MODULE 3 — Clean Claim Guarantee

### What it does
Final quality check before the claim goes to the insurer.
Nothing wrong leaves this module.

### Three steps (historical denial patterns check is out of MVP scope)

**Step 1 - Medical Code and Integrity Check**
ICD-10 codes identify the diagnosis.
CPT/procedure codes identify the treatment.
This step:
- Verifies ICD-10 code exists and is valid
- Verifies procedure code exists and is valid
- Cross-checks that they match each other logically
  (a cardiology procedure code should not be paired with a dermatology diagnosis)
- Suggests auto-corrections for common errors

Use a local lookup of valid ICD-10 codes.
Flag mismatches for human review.

**Step 2 - Document Completeness Scan**
Generate a checklist of required documents for this specific claim.
Check the documents field in the claim JSON.
For each required document that is marked false, flag it.

Required documents vary by claim type:
- All claims: hospital bill, discharge summary, id proof
- Surgical claims: add OT notes, anaesthesia records
- ICU claims: add daily ICU notes
- Emergency claims: add emergency admission certificate

Output a specific list of what is missing with document names.

**Step 3 - Final Submission Package Assembly (LLM)**
Bundle everything together:
- Validated claim JSON
- All document references
- Coverage summary from M2
- Auto-filled TPA form fields
- FHIR-compliant JSON payload for insurer API

If any document is missing or any code is flagged: hold and notify.
If everything passes: mark as submission-ready.

### Output
Single complete submission-ready claim packet.
Status updated to "Ready for Submission".

### API Endpoint
```
POST /submit-claim
Body: { validated_claim_json }
Response: { submission_package, status, missing_items }
```

---

## REACT FRONTEND — SCREENS

The UI is a step-by-step flow. Four screens total.

**Screen 1 - Upload Page**
- Drag and drop PDF upload area
- Or structured input form as alternative
- Submit button triggers M1
- Show loading state while processing

**Screen 2 - Extraction Results Page**
- Document Integrity Check card at top (fraud detection results):
  - Low risk: green border, shield icon, "Document Verified - No Tampering Detected"
  - Medium risk: yellow border, warning icon, findings list with severity badges
  - High risk: red border, alert icon, detailed findings with risk score
  - Structured input (no PDF): no fraud card shown
- Show the extracted claim JSON in a readable card format
- Not raw JSON - display it as labelled fields
- Patient info card, hospital info card, billing breakdown, documents checklist
- "Looks correct? Proceed to Policy Validation" button

**Screen 3 - Policy Validation Page**
- Upload policy PDF input
- Show validation results for each rule as PASS/FAIL/WARNING badges
- Show coverage summary in plain English
- Show patient liability vs insurer liability calculation
- If all pass: "Proceed to Final Check" button
- If failures: show specific reasons and what to fix

**Screen 4 - Submission Package Page**
- Show final checklist: all documents, all codes, all rules
- Green ticks for passed items, red flags for issues
- Show the final submission package preview
- "Submit Claim" button (for demo: shows success state with claim reference number)

---

## GEMINI PROMPT TEMPLATES

### M1 Extraction Prompt
```
You are a medical insurance claims data extractor for the Indian market.

Extract all available information from the following medical document text and
return it as a JSON object matching this exact schema. If a field cannot be found
in the document, use null for strings and 0 for numbers. Do not guess or infer
values that are not present in the document.

Return ONLY the JSON object. No explanation, no markdown, no extra text.

Schema:
{
  "patient": { "name", "dob", "gender", "abha_id", "phone", "email", "policy_number" },
  "hospital": { "hospital_id", "name", "doctor_name", "department", "tpa_name" },
  "admission": { "admission_date", "discharge_date", "admission_type", "ward_type", "room_type", "length_of_stay" },
  "medical": { "primary_diagnosis", "icd10_code", "secondary_diagnosis", "secondary_icd10", "procedure", "procedure_code" },
  "billing": { "room_charges", "icu_charges", "doctor_fees", "ot_charges", "medicines", "lab_charges", "other_charges", "total_bill" },
  "insurance": { "insurer_name", "pre_auth_number" }
}

Document text:
{document_text}
```

### M2 Policy Parsing Prompt
```
You are an insurance policy rules extractor for the Indian health insurance market.

Read the following insurance policy document and extract all coverage rules into
a structured JSON object. Be precise. Use exact numbers from the policy.
Do not interpret or infer - only extract what is explicitly stated.

Return ONLY the JSON object. No explanation, no markdown, no extra text.

Extract these fields:
{
  "policy_id": "",
  "insurer": "",
  "room_rent_limit_per_day": 0,
  "waiting_period_days": 0,
  "exclusions": [],
  "copay_percentage": 0,
  "sub_limits": {},
  "cashless_eligible": true/false,
  "reimbursement_eligible": true/false,
  "pre_auth_required": true/false,
  "sum_insured": 0,
  "network_hospitals_only": true/false
}

Policy document text:
{policy_text}
```

### M2 Coverage Summary Prompt
```
You are a health insurance claims advisor writing for patients and hospital staff
in India. Write in plain simple English. No insurance jargon.

Based on the validation results below, write a clear summary explaining:
1. What is covered by the policy for this claim
2. What is not covered and exactly why
3. How much the patient owes vs how much the insurer will pay
4. What documents or information are still missing

Keep each point to one or two sentences. Use rupee amounts where relevant.
Write as if explaining to someone who has never read an insurance policy.

Validation results:
{validation_results}

Claim details:
{claim_summary}
```

---

## ENVIRONMENT SETUP

```bash
# Backend
cd backend
pip install -r requirements.txt
# Or manually:
# pip install fastapi uvicorn python-multipart PyPDF2 pdfplumber
# pip install pytesseract Pillow google-genai psycopg2-binary python-dotenv
# pip install pdf2image cryptography pydantic-settings python-dateutil

# Install Tesseract (for Tier 3 OCR)
# Ubuntu/Debian: sudo apt install tesseract-ocr
# Mac: brew install tesseract
# Windows: download installer from GitHub

# Install Poppler (required for Tier 4 Vision OCR and fraud detection)
# Ubuntu/Debian: sudo apt install poppler-utils
# Mac: brew install poppler
# Windows: winget install oschwartz10612.Poppler
# Note: On Windows, the backend auto-detects the winget install location.

# Create .env file (copy from .env.example)
cp .env.example .env
# Then edit .env and set:
GEMINI_API_KEY=your_key_here     # Get from https://aistudio.google.com/apikey
DATABASE_URL=postgresql://user:password@localhost/claimsense
SECRET_KEY=your_secret_here

# Run backend
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## WHAT TO DEMO ON HACKATHON DAY

**Live demo flow:**
1. Upload a real hospital bill PDF
2. Show M1 extracting all fields into the claim card
3. Upload a Star Health policy PDF
4. Show M2 validating each rule with PASS/FAIL badges
5. Show the plain English coverage summary
6. Show M3 document checklist and final submission package
7. Click Submit - show success state with claim reference number

**Pre-cache these for safety:**
- Have one pre-processed claim result saved so if Gemini API is slow,
  you can show the output instantly
- Have a pre-built submission package to show M3 output

**Lines to say during demo:**
- "17% of claims in India are rejected for administrative reasons.
   ClaimSense.ai catches all of them before the claim is submitted."
- "The policy rules engine uses fixed Python logic, not AI.
   Coverage decisions are always consistent and auditable."
- "We did not invent any of this technology. We connected it."

---

## IMPORTANT DESIGN DECISIONS (do not change these)

1. All LLM calls go through one `call_llm()` function. Never call Gemini directly.

2. M2 validation uses Python if-else logic only. Never use LLM for PASS/FAIL decisions.

3. The claim JSON schema is fixed. Both frontend and backend depend on it.
   Any change must be coordinated across M1, M2, M3, and the frontend.

4. The policy rules JSON is cached per policy. The LLM parses it once.
   Do not call the LLM again for the same policy.

5. This is built for the Indian market specifically:
   - Use INR (rupees) for all amounts
   - ICD-10 codes follow Indian coding conventions
   - TPA names are Indian (Medi Assist, MDIndia, Star Health, HDFC Ergo)
   - ABHA ID is the Indian health ID format
   - FHIR/HL7 is the submission standard

6. Patient PII fields are encrypted before storage using AES/Fernet encryption.
   The encryption service protects: name, dob, phone, email, abha_id, policy_number.
   All encryption goes through `encryption_service.py`. Never store raw PII.

7. Vision functions (`call_llm_vision`, `call_llm_vision_json`) go through the same
   LLM abstraction layer as text functions. Switching models changes one file.

8. Fraud detection is non-blocking. If Gemini Vision fails or is unavailable,
   the pipeline continues normally. Fraud results are a sibling field in the API
   response, not part of the claim schema.

---

## WHAT IS OUT OF SCOPE FOR MVP

- M4 Fraud Graph Network (document-level fraud IS implemented; graph network analysis is out of scope)
- M5 Zero Wait Discharge (explain in presentation, no live code)
- Real insurer API integration (simulate with mock response)
- Payment processing
- Real encryption and security hardening
- Multi-user authentication
- Production database setup

---

## FOLDER STRUCTURE (Team Assignment)

```
claimsense-ai/
├── backend/
│   ├── main.py                  ← SHARED (don't touch once set up)
│   ├── config.py                ← SHARED
│   ├── models/
│   │   └── claim_schema.py      ← SHARED CONTRACT (nobody changes this alone)
│   │
│   ├── modules/
│   │   ├── m1_doctriage.py      ← 👤 PERSON A (works independently)
│   │   ├── m2_policy_engine.py  ← 👤 PERSON B (works independently)
│   │   └── m3_clean_claim.py    ← 👤 PERSON C (works independently)
│   │
│   ├── services/
│   │   ├── llm_service.py       ← SHARED (everyone calls call_llm())
│   │   ├── ocr_service.py       ← 👤 PERSON A (only M1 needs this)
│   │   ├── pdf_service.py       ← 👤 PERSON A (only M1 needs this)
│   │   └── encryption_service.py ← SHARED (PII encryption before storage)
│   │
│   ├── routes/
│   │   ├── upload.py            ← 👤 PERSON A
│   │   ├── validate.py          ← 👤 PERSON B
│   │   └── submit.py            ← 👤 PERSON C
│   │
├── frontend/                    ← 👤 PERSON D (works independently)
```
