import { useState, useEffect } from 'react'
import { validatePolicyDemo } from '../api.js'

export default function ValidationPage({ claim, validationData, onComplete, onBack, onClaimUpdate }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(validationData);
  const [editableClaim, setEditableClaim] = useState(claim ? JSON.parse(JSON.stringify(claim)) : null);
  const [showEditor, setShowEditor] = useState(false);
  const [editingField, setEditingField] = useState(null);

  useEffect(() => {
    if (!results && claim) {
      runValidation();
    }
  }, []);

  async function runValidation() {
    setLoading(true);
    setError('');
    try {
      const data = await validatePolicyDemo(editableClaim || claim);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRevalidate() {
    // Push edits up to parent
    if (onClaimUpdate) onClaimUpdate(editableClaim);
    setResults(null);
    setShowEditor(false);
    setLoading(true);
    setError('');
    try {
      const data = await validatePolicyDemo(editableClaim);
      setResults(data);
    } catch (err) {
      setError(err.message);
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

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <div className="loading-text">Running policy validation rules...</div>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Checking 8 deterministic rules
        </p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="page-header">
        <h1>Policy Validation</h1>
        {error && <div className="error-banner">⚠️ {error}</div>}
        <button className="btn btn-primary" onClick={runValidation}>🔄 Retry Validation</button>
      </div>
    );
  }

  const passCount = results.validation_results?.filter(r => r.status === 'PASS').length || 0;
  const failCount = results.validation_results?.filter(r => r.status === 'FAIL').length || 0;
  const warnCount = results.validation_results?.filter(r => r.status === 'WARNING').length || 0;
  const totalBill = editableClaim?.billing?.total_bill || 0;

  const copayResult = results.validation_results?.find(r => r.rule === 'copay');
  const patientPays = copayResult?.amount || 0;
  const insurerPays = totalBill - patientPays;

  const hasIssues = failCount > 0 || warnCount > 0;

  return (
    <div>
      <div className="page-header">
        <h1>Policy Validation Results</h1>
        <p>
          Using{' '}
          <strong style={{ color: 'var(--accent-primary)' }}>
            {results.policy_rules?.insurer || 'Demo Policy'}
          </strong>
          {' '}• Sum Insured: ₹{(results.policy_rules?.sum_insured || 0).toLocaleString('en-IN')}
        </p>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* Summary Stats */}
      <div style={{ display: 'flex', gap: 'var(--space-md)', justifyContent: 'center', marginBottom: 'var(--space-xl)', flexWrap: 'wrap' }}>
        <StatBadge label="Passed" count={passCount} color="var(--success)" bg="var(--success-bg)" />
        <StatBadge label="Failed" count={failCount} color="var(--danger)" bg="var(--danger-bg)" />
        <StatBadge label="Warnings" count={warnCount} color="var(--warning)" bg="var(--warning-bg)" />
      </div>

      {/* Overall Status */}
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-xl)' }}>
        <span className={`badge ${results.overall_status === 'PASS' ? 'badge-pass' : results.overall_status === 'FAIL' ? 'badge-fail' : 'badge-warning'}`}
          style={{ fontSize: 'var(--font-size-sm)', padding: '6px 16px' }}>
          Overall: {results.overall_status}
        </span>
      </div>

      {/* Validation Rules */}
      <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
        <div className="card-title">📋 Rule-by-Rule Results</div>
        <div className="validation-list">
          {results.validation_results?.map((r, i) => (
            <div key={i} className="validation-item">
              <span className={`badge badge-${r.status.toLowerCase()}`}>
                {r.status === 'PASS' ? '✓' : r.status === 'FAIL' ? '✗' : '⚠'} {r.status}
              </span>
              <span className="rule-name">{formatRuleName(r.rule)}</span>
              <span className="rule-reason">{r.reason}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Fix Issues Panel — show when there are failures/warnings */}
      {hasIssues && (
        <div style={{
          border: '1px solid var(--warning)',
          background: 'var(--warning-bg)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-xl)',
          marginBottom: 'var(--space-lg)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
            <span style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)' }}>
              ⚠️ Fix Issues & Revalidate
            </span>
            <button
              className="btn btn-secondary"
              onClick={() => setShowEditor(!showEditor)}
              style={{ padding: '6px 14px', fontSize: 'var(--font-size-sm)' }}
            >
              {showEditor ? '▲ Hide Editor' : '▼ Edit Fields'}
            </button>
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: showEditor ? 'var(--space-md)' : '0' }}>
            Some checks failed or have warnings. Edit the missing fields below and click Revalidate.
          </p>

          {showEditor && editableClaim && (
            <div style={{ marginTop: 'var(--space-md)' }}>
              <div className="card-grid" style={{ gap: '12px' }}>
                {/* Patient */}
                <div className="card" style={{ padding: '16px' }}>
                  <div className="card-title" style={{ fontSize: 'var(--font-size-sm)' }}>👤 Patient</div>
                  <EditRow label="Name" value={editableClaim.patient?.name} onChange={v => updateField('patient', 'name', v)} />
                  <EditRow label="DOB" value={editableClaim.patient?.dob} onChange={v => updateField('patient', 'dob', v)} />
                  <EditRow label="Gender" value={editableClaim.patient?.gender} onChange={v => updateField('patient', 'gender', v)} />
                  <EditRow label="ABHA ID" value={editableClaim.patient?.abha_id} onChange={v => updateField('patient', 'abha_id', v)} />
                  <EditRow label="Policy No." value={editableClaim.patient?.policy_number} onChange={v => updateField('patient', 'policy_number', v)} />
                </div>

                {/* Medical */}
                <div className="card" style={{ padding: '16px' }}>
                  <div className="card-title" style={{ fontSize: 'var(--font-size-sm)' }}>🩺 Medical</div>
                  <EditRow label="Diagnosis" value={editableClaim.medical?.primary_diagnosis} onChange={v => updateField('medical', 'primary_diagnosis', v)} />
                  <EditRow label="ICD-10" value={editableClaim.medical?.icd10_code} onChange={v => updateField('medical', 'icd10_code', v)} />
                  <EditRow label="Procedure" value={editableClaim.medical?.procedure} onChange={v => updateField('medical', 'procedure', v)} />
                  <EditRow label="Proc. Code" value={editableClaim.medical?.procedure_code} onChange={v => updateField('medical', 'procedure_code', v)} />
                </div>

                {/* Admission */}
                <div className="card" style={{ padding: '16px' }}>
                  <div className="card-title" style={{ fontSize: 'var(--font-size-sm)' }}>🛏️ Admission</div>
                  <EditRow label="Admission Date" value={editableClaim.admission?.admission_date} onChange={v => updateField('admission', 'admission_date', v)} />
                  <EditRow label="Discharge Date" value={editableClaim.admission?.discharge_date} onChange={v => updateField('admission', 'discharge_date', v)} />
                  <EditRow label="Stay (days)" value={editableClaim.admission?.length_of_stay} onChange={v => updateField('admission', 'length_of_stay', parseInt(v) || 0)} type="number" />
                  <EditRow label="Ward" value={editableClaim.admission?.ward_type} onChange={v => updateField('admission', 'ward_type', v)} />
                </div>

                {/* Billing */}
                <div className="card" style={{ padding: '16px' }}>
                  <div className="card-title" style={{ fontSize: 'var(--font-size-sm)' }}>💰 Billing (₹)</div>
                  <EditRow label="Room Charges" value={editableClaim.billing?.room_charges} onChange={v => updateField('billing', 'room_charges', parseFloat(v) || 0)} type="number" />
                  <EditRow label="ICU Charges" value={editableClaim.billing?.icu_charges} onChange={v => updateField('billing', 'icu_charges', parseFloat(v) || 0)} type="number" />
                  <EditRow label="Doctor Fees" value={editableClaim.billing?.doctor_fees} onChange={v => updateField('billing', 'doctor_fees', parseFloat(v) || 0)} type="number" />
                  <EditRow label="Total Bill" value={editableClaim.billing?.total_bill} onChange={v => updateField('billing', 'total_bill', parseFloat(v) || 0)} type="number" />
                </div>

                {/* Documents toggles */}
                <div className="card" style={{ padding: '16px' }}>
                  <div className="card-title" style={{ fontSize: 'var(--font-size-sm)' }}>📄 Documents</div>
                  <ToggleRow label="Hospital Bill" value={editableClaim.documents?.hospital_bill} onToggle={() => updateField('documents', 'hospital_bill', !editableClaim.documents?.hospital_bill)} />
                  <ToggleRow label="Discharge Summary" value={editableClaim.documents?.discharge_summary} onToggle={() => updateField('documents', 'discharge_summary', !editableClaim.documents?.discharge_summary)} />
                  <ToggleRow label="Prescription" value={editableClaim.documents?.prescription} onToggle={() => updateField('documents', 'prescription', !editableClaim.documents?.prescription)} />
                  <ToggleRow label="Lab Reports" value={editableClaim.documents?.lab_reports} onToggle={() => updateField('documents', 'lab_reports', !editableClaim.documents?.lab_reports)} />
                  <ToggleRow label="Pre-Auth Letter" value={editableClaim.documents?.pre_auth_letter} onToggle={() => updateField('documents', 'pre_auth_letter', !editableClaim.documents?.pre_auth_letter)} />
                  <ToggleRow label="ID Proof" value={editableClaim.documents?.id_proof} onToggle={() => updateField('documents', 'id_proof', !editableClaim.documents?.id_proof)} />
                </div>

                {/* Insurance */}
                <div className="card" style={{ padding: '16px' }}>
                  <div className="card-title" style={{ fontSize: 'var(--font-size-sm)' }}>🛡️ Insurance</div>
                  <EditRow label="Insurer" value={editableClaim.insurance?.insurer_name} onChange={v => updateField('insurance', 'insurer_name', v)} />
                  <EditRow label="Pre-Auth #" value={editableClaim.insurance?.pre_auth_number} onChange={v => updateField('insurance', 'pre_auth_number', v)} />
                </div>
              </div>

              <div style={{ textAlign: 'center', marginTop: 'var(--space-lg)' }}>
                <button className="btn btn-primary" onClick={handleRevalidate}
                  style={{ padding: '12px 32px', fontSize: '1rem' }}>
                  🔄 Revalidate with Updated Fields
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Liability Breakdown */}
      <div className="card-grid" style={{ marginBottom: 'var(--space-lg)' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
            Insurer Pays
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--success)' }}>
            ₹{insurerPays.toLocaleString('en-IN')}
          </div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
            Patient Pays
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--warning)' }}>
            ₹{patientPays.toLocaleString('en-IN')}
          </div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
            Total Bill
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--accent-primary)' }}>
            ₹{totalBill.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Coverage Summary */}
      {results.coverage_summary && (
        <div className="card">
          <div className="card-title">📝 Coverage Summary</div>
          <div className="summary-box">
            {results.coverage_summary.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        </div>
      )}

      <div className="action-bar">
        <button className="btn btn-secondary" onClick={onBack}>← Back</button>
        <button className="btn btn-primary" onClick={() => onComplete(results)}>
          Proceed to Final Check →
        </button>
      </div>
    </div>
  );
}

/* ── Helpers ── */

function EditRow({ label, value, onChange, type = 'text' }) {
  return (
    <div style={{ marginBottom: '8px' }}>
      <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px', fontWeight: 500 }}>
        {label}
      </label>
      <input
        type={type}
        value={value ?? ''}
        onChange={e => onChange(e.target.value)}
        style={{
          width: '100%', padding: '6px 10px', fontSize: 'var(--font-size-sm)',
          border: '1px solid var(--border)', borderRadius: '6px',
          background: 'var(--bg-primary)', color: 'var(--text-primary)',
          outline: 'none',
        }}
        onFocus={e => e.target.style.borderColor = 'var(--accent)'}
        onBlur={e => e.target.style.borderColor = 'var(--border)'}
      />
    </div>
  );
}

function ToggleRow({ label, value, onToggle }) {
  return (
    <div
      onClick={onToggle}
      style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '6px 0', cursor: 'pointer', fontSize: 'var(--font-size-sm)',
      }}
    >
      <span>{label}</span>
      <span>{value ? '✅' : '❌'}</span>
    </div>
  );
}

function StatBadge({ label, count, color, bg }) {
  return (
    <div style={{
      background: bg,
      border: `1px solid ${color}30`,
      borderRadius: 'var(--radius-md)',
      padding: 'var(--space-md) var(--space-xl)',
      textAlign: 'center',
      minWidth: '120px',
    }}>
      <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color }}>{count}</div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>{label}</div>
    </div>
  );
}

function formatRuleName(rule) {
  return rule
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}
