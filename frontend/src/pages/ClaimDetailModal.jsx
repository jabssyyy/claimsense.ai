import { useState, useEffect } from 'react';
import { validatePolicyDemo, submitClaim } from '../api.js';

export default function ClaimDetailModal({ claimId, onClose, onLoadIntoWizard }) {
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('details'); // 'details', 'edit', 'validate', 'submit'
  const [editableClaim, setEditableClaim] = useState(null);
  const [validationResults, setValidationResults] = useState(null);
  const [validating, setValidating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (claimId) fetchClaim();
  }, [claimId]);

  async function fetchClaim() {
    try {
      setLoading(true);
      const res = await fetch(`/api/claims/${claimId}`);
      if (!res.ok) throw new Error('Failed to fetch claim');
      const data = await res.json();
      setClaim(data);
      setEditableClaim(data.raw_data ? JSON.parse(JSON.stringify(data.raw_data)) : null);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function updateField(section, field, value) {
    setEditableClaim(prev => {
      const updated = JSON.parse(JSON.stringify(prev));
      if (!updated[section]) updated[section] = {};
      updated[section][field] = value;
      return updated;
    });
  }

  async function handleValidate() {
    setValidating(true);
    setError('');
    try {
      const data = await validatePolicyDemo(editableClaim);
      setValidationResults(data);
      setTab('validate');
    } catch (err) {
      setError(err.message);
    } finally {
      setValidating(false);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError('');
    try {
      const result = await submitClaim(
        editableClaim,
        validationResults?.validation_results || [],
        validationResults?.coverage_summary || null,
      );
      setSubmitResult(result);
      setTab('submit');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!claimId) return null;

  const rawData = editableClaim || claim?.raw_data || {};

  function renderSection(title, icon, section, fields) {
    return (
      <div style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '8px' }}>
          {icon} {title}
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '6px' }}>
          {fields.map(([field, label, type]) => {
            const val = rawData[section]?.[field];
            if (tab === 'edit') {
              if (type === 'bool') {
                return (
                  <div key={field} onClick={() => updateField(section, field, !val)}
                    style={{
                      padding: '6px 10px', background: 'var(--surface)', borderRadius: '6px',
                      border: '1px solid var(--border)', cursor: 'pointer',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      fontSize: 'var(--font-size-sm)',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{label}</span>
                    <span>{val ? '✓ Yes' : '✗ No'}</span>
                  </div>
                );
              }
              return (
                <div key={field} style={{ padding: '4px 0' }}>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px' }}>{label}</label>
                  <input
                    type={type === 'number' ? 'number' : 'text'}
                    value={rawData[section]?.[field] ?? ''}
                    onChange={e => updateField(section, field, type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)}
                    style={{
                      width: '100%', padding: '5px 8px', fontSize: 'var(--font-size-sm)',
                      border: '1px solid var(--border)', borderRadius: '6px',
                      background: 'var(--bg-primary)', color: 'var(--text-primary)', outline: 'none',
                    }}
                  />
                </div>
              );
            }
            // Read-only view
            if (val === null || val === undefined || val === '' || val === 0 || val === false) return null;
            return (
              <div key={field} style={{
                padding: '6px 10px', background: 'var(--surface)',
                borderRadius: '6px', border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{label}</div>
                <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
                  {typeof val === 'boolean' ? (val ? '✓ Yes' : '✗ No') : String(val)}
                </div>
              </div>
            );
          }).filter(Boolean)}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'var(--bg-overlay)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: '20px',
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-primary)', borderRadius: '16px',
        maxWidth: '900px', width: '100%', maxHeight: '90vh',
        overflow: 'auto', boxShadow: 'var(--shadow-float)',
        padding: '24px',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>Claim Details</h2>
            {claim && <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontSize: 'var(--font-size-sm)' }}>{claim.claim_id}</span>}
          </div>
          <button onClick={onClose} style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: '8px', padding: '6px 14px', cursor: 'pointer',
            fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)',
          }}>✕ Close</button>
        </div>

        {/* Tab Bar */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '16px', flexWrap: 'wrap' }}>
          {[
            ['details', 'Details'],
            ['edit', 'Edit'],
            ['validate', 'Validate'],
            ['submit', 'Submit'],
          ].map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} style={{
              padding: '6px 16px', fontSize: 'var(--font-size-sm)', fontWeight: 600,
              borderRadius: '8px', cursor: 'pointer', border: 'none',
              background: tab === key ? 'var(--accent)' : 'var(--surface)',
              color: tab === key ? '#fff' : 'var(--text-secondary)',
              transition: 'all 0.15s',
            }}>{label}</button>
          ))}
        </div>

        {loading && <p style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading...</p>}

        {error && <div className="error-banner" style={{ marginBottom: '12px' }}>{error}</div>}

        {!loading && claim && (tab === 'details' || tab === 'edit') && (
          <>
            {/* Status bar */}
            <div style={{
              padding: '10px 14px', borderRadius: '10px', marginBottom: '16px',
              background: 'var(--accent-lighter)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              fontSize: 'var(--font-size-sm)',
            }}>
              <span><strong>Status:</strong> {claim.status}</span>
              {claim.total_bill > 0 && <span style={{ fontWeight: 700, color: 'var(--accent)' }}>
                ₹{Number(claim.total_bill).toLocaleString('en-IN')}
              </span>}
            </div>

            {renderSection('Patient', '', 'patient', [
              ['name', 'Name'], ['dob', 'DOB'], ['gender', 'Gender'], ['abha_id', 'ABHA ID'],
              ['phone', 'Phone'], ['policy_number', 'Policy No.'],
            ])}
            {renderSection('Hospital', '', 'hospital', [
              ['name', 'Hospital'], ['doctor_name', 'Doctor'], ['department', 'Department'], ['tpa_name', 'TPA'],
            ])}
            {renderSection('Admission', '', 'admission', [
              ['admission_date', 'Admission'], ['discharge_date', 'Discharge'], ['admission_type', 'Type'],
              ['ward_type', 'Ward'], ['room_type', 'Room'], ['length_of_stay', 'Stay (days)', 'number'],
            ])}
            {renderSection('Medical', '', 'medical', [
              ['primary_diagnosis', 'Diagnosis'], ['icd10_code', 'ICD-10'], ['procedure', 'Procedure'], ['procedure_code', 'Proc. Code'],
            ])}
            {renderSection('Billing', '', 'billing', [
              ['room_charges', 'Room', 'number'], ['icu_charges', 'ICU', 'number'], ['doctor_fees', 'Doctor', 'number'],
              ['ot_charges', 'OT', 'number'], ['medicines', 'Medicines', 'number'], ['lab_charges', 'Lab', 'number'],
              ['total_bill', 'Total', 'number'],
            ])}
            {renderSection('Documents', '', 'documents', [
              ['hospital_bill', 'Hospital Bill', 'bool'], ['discharge_summary', 'Discharge Summary', 'bool'],
              ['prescription', 'Prescription', 'bool'], ['lab_reports', 'Lab Reports', 'bool'],
              ['pre_auth_letter', 'Pre-Auth Letter', 'bool'], ['id_proof', 'ID Proof', 'bool'],
            ])}
            {renderSection('Insurance', '', 'insurance', [
              ['insurer_name', 'Insurer'], ['pre_auth_number', 'Pre-Auth #'],
            ])}

            {tab === 'edit' && (
              <div style={{ textAlign: 'center', marginTop: '16px' }}>
                <button className="btn btn-primary" onClick={handleValidate} disabled={validating}
                  style={{ padding: '10px 28px' }}>
                  {validating ? 'Validating...' : 'Run Validation'}
                </button>
              </div>
            )}
          </>
        )}

        {/* Validation Results Tab */}
        {!loading && tab === 'validate' && validationResults && (
          <div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
              <MiniStat label="Passed" count={validationResults.validation_results?.filter(r => r.status === 'PASS').length || 0} color="var(--success)" />
              <MiniStat label="Failed" count={validationResults.validation_results?.filter(r => r.status === 'FAIL').length || 0} color="var(--danger)" />
              <MiniStat label="Warnings" count={validationResults.validation_results?.filter(r => r.status === 'WARNING').length || 0} color="var(--warning)" />
            </div>

            <div className="validation-list" style={{ marginBottom: '16px' }}>
              {validationResults.validation_results?.map((r, i) => (
                <div key={i} className="validation-item">
                  <span className={`badge badge-${r.status.toLowerCase()}`}>
                    {r.status === 'PASS' ? '✓' : r.status === 'FAIL' ? '✗' : '⚠'} {r.status}
                  </span>
                  <span className="rule-name">{r.rule.replace(/_/g, ' ')}</span>
                  <span className="rule-reason">{r.reason}</span>
                </div>
              ))}
            </div>

            {validationResults.coverage_summary && (
              <div className="card" style={{ padding: '14px', marginBottom: '16px' }}>
                <div className="card-title" style={{ fontSize: 'var(--font-size-sm)' }}>Coverage Summary</div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                  {validationResults.coverage_summary}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button className="btn btn-secondary" onClick={() => setTab('edit')}>
                ← Back to Edit
              </button>
              <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting}>
                {submitting ? 'Submitting...' : 'Submit Claim'}
              </button>
            </div>
          </div>
        )}

        {!loading && tab === 'validate' && !validationResults && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p style={{ color: 'var(--text-muted)' }}>No validation results yet. Go to Edit tab and run validation.</p>
          </div>
        )}

        {/* Submit Result Tab */}
        {!loading && tab === 'submit' && submitResult && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{ fontSize: '3rem', marginBottom: '12px' }}>—</div>
            <h3 style={{ marginBottom: '8px' }}>Claim Submitted Successfully</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>
              Reference: <strong style={{ color: 'var(--accent)' }}>{submitResult.claim_reference || submitResult.submission_package?.claim_reference}</strong>
            </p>
            <button className="btn btn-primary" onClick={onClose}>Close</button>
          </div>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, count, color }) {
  return (
    <div style={{
      padding: '8px 20px', borderRadius: '8px', textAlign: 'center',
      background: `${color}15`, border: `1px solid ${color}30`,
    }}>
      <div style={{ fontSize: '1.3rem', fontWeight: 700, color }}>{count}</div>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
    </div>
  );
}
