import { useState } from 'react';

export default function ExtractionPage({ claim, fraudDetection, onComplete, onBack, onClaimUpdate }) {
  const [editableClaim, setEditableClaim] = useState(JSON.parse(JSON.stringify(claim)));
  const [editingField, setEditingField] = useState(null); // "section.field"
  const [isRevalidating, setIsRevalidating] = useState(false);

  if (!claim) return null;

  const fmt = (v) => v ?? '—';
  const fmtMoney = (v) => v ? `₹${Number(v).toLocaleString('en-IN')}` : '₹0';

  // Fraud detection helpers
  const riskColors = {
    low: { border: 'var(--success)', bg: 'var(--success-bg)', badge: 'badge-pass' },
    medium: { border: 'var(--warning)', bg: 'var(--warning-bg)', badge: 'badge-warning' },
    high: { border: 'var(--danger)', bg: 'var(--danger-bg)', badge: 'badge-fail' },
    unknown: { border: 'var(--text-muted)', bg: 'var(--bg-glass)', badge: 'badge-warning' },
  };
  const severityBadge = (severity) => {
    const map = { low: 'badge-pass', medium: 'badge-warning', high: 'badge-fail' };
    return map[severity] || 'badge-warning';
  };
  const riskLevel = fraudDetection?.risk_level || 'unknown';
  const riskStyle = riskColors[riskLevel] || riskColors.unknown;

  // Inline edit helpers
  function updateField(section, field, value) {
    setEditableClaim(prev => {
      const updated = JSON.parse(JSON.stringify(prev));
      if (!updated[section]) updated[section] = {};
      updated[section][field] = value;
      return updated;
    });
  }

  function startEdit(key) {
    setEditingField(key);
  }

  function stopEdit() {
    setEditingField(null);
    if (onClaimUpdate) onClaimUpdate(editableClaim);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') stopEdit();
    if (e.key === 'Escape') {
      setEditingField(null);
      setEditableClaim(JSON.parse(JSON.stringify(claim)));
    }
  }

  // Revalidate
  async function handleRevalidate() {
    setIsRevalidating(true);
    try {
      if (onClaimUpdate) onClaimUpdate(editableClaim);
      const res = await fetch('/api/validate-policy-demo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claim_json: editableClaim }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Validation failed');
      }
      const data = await res.json();
      onComplete(data);
    } catch (err) {
      alert('Revalidation failed: ' + err.message);
    } finally {
      setIsRevalidating(false);
    }
  }

  // Editable field component
  function EditableField({ section, field, label, value, isMoney }) {
    const key = `${section}.${field}`;
    const isEditing = editingField === key;
    const displayValue = isMoney ? fmtMoney(value) : fmt(value);

    if (isEditing) {
      return (
        <div className="info-row">
          <span className="info-label">{label}</span>
          <input
            type={isMoney ? 'number' : 'text'}
            value={editableClaim[section]?.[field] ?? ''}
            onChange={e => updateField(section, field, isMoney ? parseFloat(e.target.value) || 0 : e.target.value)}
            onBlur={stopEdit}
            onKeyDown={handleKeyDown}
            autoFocus
            style={{
              flex: 1, padding: '4px 8px', fontSize: 'var(--font-size-sm)',
              border: '2px solid var(--accent)', borderRadius: '6px',
              background: 'var(--surface)', color: 'var(--text-primary)',
              outline: 'none', maxWidth: '200px',
            }}
          />
        </div>
      );
    }

    return (
      <div className="info-row" onClick={() => startEdit(key)}
        style={{ cursor: 'pointer', transition: 'background 0.15s', borderRadius: '4px' }}
        onMouseOver={e => e.currentTarget.style.background = 'var(--accent-lighter)'}
        onMouseOut={e => e.currentTarget.style.background = 'transparent'}
        title="Click to edit"
      >
        <span className="info-label">{label}</span>
        <span className="info-value" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {displayValue}
          <span style={{ fontSize: '10px', opacity: 0.4 }}>edit</span>
        </span>
      </div>
    );
  }

  // Editable boolean toggle for documents
  function ToggleField({ section, field, label }) {
    const val = editableClaim[section]?.[field];
    return (
      <div className="info-row"
        onClick={() => updateField(section, field, !val)}
        style={{ cursor: 'pointer', transition: 'background 0.15s', borderRadius: '4px' }}
        onMouseOver={e => e.currentTarget.style.background = 'var(--accent-lighter)'}
        onMouseOut={e => e.currentTarget.style.background = 'transparent'}
        title="Click to toggle"
      >
        <span className="info-label">{label}</span>
        <span className="info-value">{val ? '✓' : '✗'} <span style={{ fontSize: '10px', opacity: 0.4 }}>toggle</span></span>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Extracted Claim Data</h1>
        <p>Click any field to edit it. Then click "Validate with Edits" to re-run policy checks.</p>
      </div>

      {/* ── Fraud Detection Alert ── */}
      {fraudDetection && (
        <div style={{
          border: `1px solid ${riskStyle.border}`,
          background: riskStyle.bg,
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-xl)',
          marginBottom: 'var(--space-xl)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
              <span style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)' }}>
                Document Integrity Check
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
              <span className={`badge ${riskStyle.badge}`}>
                {riskLevel.toUpperCase()} RISK
              </span>
              <span style={{
                fontFamily: 'monospace',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--text-secondary)',
              }}>
                Score: {((fraudDetection.risk_score || 0) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          {fraudDetection.summary && (
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
              {fraudDetection.summary}
            </p>
          )}
          {fraudDetection.findings && fraudDetection.findings.length > 0 && (
            <div className="validation-list">
              {fraudDetection.findings.map((finding, i) => (
                <div key={i} className="validation-item">
                  <span className={`badge ${severityBadge(finding.severity)}`}>
                    {(finding.severity || 'info').toUpperCase()}
                  </span>
                  <span className="rule-name" style={{ textTransform: 'none' }}>
                    {(finding.type || 'finding').replace(/_/g, ' ')}
                  </span>
                  <span className="rule-reason">{finding.description}</span>
                </div>
              ))}
            </div>
          )}
          {riskLevel === 'low' && (!fraudDetection.findings || fraudDetection.findings.length === 0) && (
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--success)', fontWeight: 600 }}>
              Document Verified — No Tampering Detected
            </p>
          )}
        </div>
      )}

      {/* ── Editable Claim Cards ── */}
      <div className="card-grid">
        {/* Patient Info */}
        <div className="card">
          <div className="card-title">Patient</div>
          <EditableField section="patient" field="name" label="Name" value={editableClaim.patient?.name} />
          <EditableField section="patient" field="dob" label="DOB" value={editableClaim.patient?.dob} />
          <EditableField section="patient" field="gender" label="Gender" value={editableClaim.patient?.gender} />
          <EditableField section="patient" field="abha_id" label="ABHA ID" value={editableClaim.patient?.abha_id} />
          <EditableField section="patient" field="phone" label="Phone" value={editableClaim.patient?.phone} />
          <EditableField section="patient" field="policy_number" label="Policy No." value={editableClaim.patient?.policy_number} />
        </div>

        {/* Hospital Info */}
        <div className="card">
          <div className="card-title">Hospital</div>
          <EditableField section="hospital" field="name" label="Hospital" value={editableClaim.hospital?.name} />
          <EditableField section="hospital" field="doctor_name" label="Doctor" value={editableClaim.hospital?.doctor_name} />
          <EditableField section="hospital" field="department" label="Department" value={editableClaim.hospital?.department} />
          <EditableField section="hospital" field="tpa_name" label="TPA" value={editableClaim.hospital?.tpa_name} />
        </div>

        {/* Medical Info */}
        <div className="card">
          <div className="card-title">Medical</div>
          <EditableField section="medical" field="primary_diagnosis" label="Diagnosis" value={editableClaim.medical?.primary_diagnosis} />
          <EditableField section="medical" field="icd10_code" label="ICD-10" value={editableClaim.medical?.icd10_code} />
          <EditableField section="medical" field="procedure" label="Procedure" value={editableClaim.medical?.procedure} />
          <EditableField section="medical" field="procedure_code" label="Proc. Code" value={editableClaim.medical?.procedure_code} />
        </div>

        {/* Admission Info */}
        <div className="card">
          <div className="card-title">Admission</div>
          <EditableField section="admission" field="admission_date" label="Admission Date" value={editableClaim.admission?.admission_date} />
          <EditableField section="admission" field="discharge_date" label="Discharge Date" value={editableClaim.admission?.discharge_date} />
          <EditableField section="admission" field="admission_type" label="Type" value={editableClaim.admission?.admission_type} />
          <EditableField section="admission" field="ward_type" label="Ward" value={editableClaim.admission?.ward_type} />
          <EditableField section="admission" field="room_type" label="Room" value={editableClaim.admission?.room_type} />
          <EditableField section="admission" field="length_of_stay" label="Stay (days)" value={editableClaim.admission?.length_of_stay} />
        </div>

        {/* Billing Breakdown */}
        <div className="card">
          <div className="card-title">Billing Breakdown</div>
          <EditableField section="billing" field="room_charges" label="Room Charges" value={editableClaim.billing?.room_charges} isMoney />
          <EditableField section="billing" field="icu_charges" label="ICU Charges" value={editableClaim.billing?.icu_charges} isMoney />
          <EditableField section="billing" field="doctor_fees" label="Doctor Fees" value={editableClaim.billing?.doctor_fees} isMoney />
          <EditableField section="billing" field="ot_charges" label="OT Charges" value={editableClaim.billing?.ot_charges} isMoney />
          <EditableField section="billing" field="medicines" label="Medicines" value={editableClaim.billing?.medicines} isMoney />
          <EditableField section="billing" field="lab_charges" label="Lab Charges" value={editableClaim.billing?.lab_charges} isMoney />
          <div className="info-row" style={{ borderTop: '2px solid var(--accent-primary)', paddingTop: 'var(--space-sm)', marginTop: 'var(--space-xs)' }}>
            <span className="info-label" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Total Bill</span>
            <span className="info-value" style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--accent-primary)' }}>
              {fmtMoney(editableClaim.billing?.total_bill)}
            </span>
          </div>
        </div>

        {/* Documents & Insurance */}
        <div className="card">
          <div className="card-title">Documents & Insurance</div>
          <ToggleField section="documents" field="hospital_bill" label="Hospital Bill" />
          <ToggleField section="documents" field="discharge_summary" label="Discharge Summary" />
          <ToggleField section="documents" field="prescription" label="Prescription" />
          <ToggleField section="documents" field="lab_reports" label="Lab Reports" />
          <ToggleField section="documents" field="pre_auth_letter" label="Pre-Auth Letter" />
          <ToggleField section="documents" field="id_proof" label="ID Proof" />
          <div style={{ marginTop: 'var(--space-md)', paddingTop: 'var(--space-md)', borderTop: '1px solid var(--border-color)' }}>
            <EditableField section="insurance" field="insurer_name" label="Insurer" value={editableClaim.insurance?.insurer_name} />
            <EditableField section="insurance" field="pre_auth_number" label="Pre-Auth #" value={editableClaim.insurance?.pre_auth_number} />
          </div>
        </div>
      </div>

      {/* Claim ID Badge */}
      <div style={{ textAlign: 'center', marginTop: 'var(--space-xl)' }}>
        <span style={{
          background: 'var(--bg-glass-strong)',
          padding: '6px 16px',
          borderRadius: '999px',
          fontSize: 'var(--font-size-sm)',
          color: 'var(--text-secondary)',
        }}>
          Claim ID: <strong style={{ color: 'var(--accent-primary)' }}>{editableClaim.claim_id}</strong>
          &nbsp;•&nbsp; Type: {editableClaim.input_type}
          &nbsp;•&nbsp; Status: {editableClaim.meta?.status}
        </span>
      </div>

      <div className="action-bar">
        <button className="btn btn-secondary" onClick={onBack}>← Back</button>
        <button
          className="btn btn-primary"
          onClick={handleRevalidate}
          disabled={isRevalidating}
          style={isRevalidating ? { opacity: 0.6 } : {}}
        >
          {isRevalidating ? 'Validating...' : 'Validate with Edits →'}
        </button>
      </div>
    </div>
  );
}
