/**
 * ClaimSense.ai — API Service
 * 
 * All API calls to the FastAPI backend go through this module.
 * Base URL is proxied by Vite (in dev) from /api → http://localhost:8000/api.
 */

const BASE = '/api';

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE}/upload-document`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }

  return res.json();
}

export async function uploadMultiple(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const res = await fetch(`${BASE}/upload-multiple`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Multi-file upload failed (${res.status})`);
  }

  return res.json();
}

export async function uploadStructured(data) {
  const res = await fetch(`${BASE}/upload-structured`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Structured upload failed (${res.status})`);
  }

  return res.json();
}

export async function validatePolicyDemo(claimJson) {
  const res = await fetch(`${BASE}/validate-policy-demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim_json: claimJson }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Validation failed (${res.status})`);
  }

  return res.json();
}

export async function submitClaim(validatedClaimJson, validationResults, coverageSummary) {
  const res = await fetch(`${BASE}/submit-claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      validated_claim_json: validatedClaimJson,
      validation_results: validationResults || [],
      coverage_summary: coverageSummary || null,
      skip_fhir: true,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Submission failed (${res.status})`);
  }

  return res.json();
}
