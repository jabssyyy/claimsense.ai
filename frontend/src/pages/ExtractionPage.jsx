export default function ExtractionPage({ claim, onComplete, onBack }) {
  if (!claim) return null;

  const fmt = (v) => v ?? '—';
  const fmtMoney = (v) => v ? `₹${Number(v).toLocaleString('en-IN')}` : '₹0';

  return (
    <div>
      <div className="page-header">
        <h1>Extracted Claim Data</h1>
        <p>Review the information below before proceeding to policy validation</p>
      </div>

      <div className="card-grid">
        {/* Patient Info */}
        <div className="card">
          <div className="card-title">👤 Patient</div>
          <div className="info-row"><span className="info-label">Name</span><span className="info-value">{fmt(claim.patient?.name)}</span></div>
          <div className="info-row"><span className="info-label">DOB</span><span className="info-value">{fmt(claim.patient?.dob)}</span></div>
          <div className="info-row"><span className="info-label">Gender</span><span className="info-value">{fmt(claim.patient?.gender)}</span></div>
          <div className="info-row"><span className="info-label">ABHA ID</span><span className="info-value">{fmt(claim.patient?.abha_id)}</span></div>
          <div className="info-row"><span className="info-label">Phone</span><span className="info-value">{fmt(claim.patient?.phone)}</span></div>
          <div className="info-row"><span className="info-label">Policy No.</span><span className="info-value">{fmt(claim.patient?.policy_number)}</span></div>
        </div>

        {/* Hospital Info */}
        <div className="card">
          <div className="card-title">🏥 Hospital</div>
          <div className="info-row"><span className="info-label">Hospital</span><span className="info-value">{fmt(claim.hospital?.name)}</span></div>
          <div className="info-row"><span className="info-label">Doctor</span><span className="info-value">{fmt(claim.hospital?.doctor_name)}</span></div>
          <div className="info-row"><span className="info-label">Department</span><span className="info-value">{fmt(claim.hospital?.department)}</span></div>
          <div className="info-row"><span className="info-label">TPA</span><span className="info-value">{fmt(claim.hospital?.tpa_name)}</span></div>
        </div>

        {/* Medical Info */}
        <div className="card">
          <div className="card-title">🩺 Medical</div>
          <div className="info-row"><span className="info-label">Diagnosis</span><span className="info-value">{fmt(claim.medical?.primary_diagnosis)}</span></div>
          <div className="info-row"><span className="info-label">ICD-10</span><span className="info-value">{fmt(claim.medical?.icd10_code)}</span></div>
          <div className="info-row"><span className="info-label">Procedure</span><span className="info-value">{fmt(claim.medical?.procedure)}</span></div>
          <div className="info-row"><span className="info-label">Proc. Code</span><span className="info-value">{fmt(claim.medical?.procedure_code)}</span></div>
        </div>

        {/* Admission Info */}
        <div className="card">
          <div className="card-title">🛏️ Admission</div>
          <div className="info-row"><span className="info-label">Admission Date</span><span className="info-value">{fmt(claim.admission?.admission_date)}</span></div>
          <div className="info-row"><span className="info-label">Discharge Date</span><span className="info-value">{fmt(claim.admission?.discharge_date)}</span></div>
          <div className="info-row"><span className="info-label">Type</span><span className="info-value">{fmt(claim.admission?.admission_type)}</span></div>
          <div className="info-row"><span className="info-label">Ward</span><span className="info-value">{fmt(claim.admission?.ward_type)}</span></div>
          <div className="info-row"><span className="info-label">Room</span><span className="info-value">{fmt(claim.admission?.room_type)}</span></div>
          <div className="info-row"><span className="info-label">Stay</span><span className="info-value">{claim.admission?.length_of_stay || 0} days</span></div>
        </div>

        {/* Billing Breakdown */}
        <div className="card">
          <div className="card-title">💰 Billing Breakdown</div>
          <div className="info-row"><span className="info-label">Room Charges</span><span className="info-value">{fmtMoney(claim.billing?.room_charges)}</span></div>
          <div className="info-row"><span className="info-label">ICU Charges</span><span className="info-value">{fmtMoney(claim.billing?.icu_charges)}</span></div>
          <div className="info-row"><span className="info-label">Doctor Fees</span><span className="info-value">{fmtMoney(claim.billing?.doctor_fees)}</span></div>
          <div className="info-row"><span className="info-label">OT Charges</span><span className="info-value">{fmtMoney(claim.billing?.ot_charges)}</span></div>
          <div className="info-row"><span className="info-label">Medicines</span><span className="info-value">{fmtMoney(claim.billing?.medicines)}</span></div>
          <div className="info-row"><span className="info-label">Lab Charges</span><span className="info-value">{fmtMoney(claim.billing?.lab_charges)}</span></div>
          <div className="info-row" style={{ borderTop: '2px solid var(--accent-primary)', paddingTop: 'var(--space-sm)', marginTop: 'var(--space-xs)' }}>
            <span className="info-label" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Total Bill</span>
            <span className="info-value" style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--accent-primary)' }}>
              {fmtMoney(claim.billing?.total_bill)}
            </span>
          </div>
        </div>

        {/* Documents & Insurance */}
        <div className="card">
          <div className="card-title">📋 Documents & Insurance</div>
          <div className="info-row"><span className="info-label">Hospital Bill</span><span className="info-value">{claim.documents?.hospital_bill ? '✅' : '❌'}</span></div>
          <div className="info-row"><span className="info-label">Discharge Summary</span><span className="info-value">{claim.documents?.discharge_summary ? '✅' : '❌'}</span></div>
          <div className="info-row"><span className="info-label">Prescription</span><span className="info-value">{claim.documents?.prescription ? '✅' : '❌'}</span></div>
          <div className="info-row"><span className="info-label">Lab Reports</span><span className="info-value">{claim.documents?.lab_reports ? '✅' : '❌'}</span></div>
          <div className="info-row"><span className="info-label">Pre-Auth Letter</span><span className="info-value">{claim.documents?.pre_auth_letter ? '✅' : '❌'}</span></div>
          <div className="info-row"><span className="info-label">ID Proof</span><span className="info-value">{claim.documents?.id_proof ? '✅' : '❌'}</span></div>
          <div style={{ marginTop: 'var(--space-md)', paddingTop: 'var(--space-md)', borderTop: '1px solid var(--border-color)' }}>
            <div className="info-row"><span className="info-label">Insurer</span><span className="info-value">{fmt(claim.insurance?.insurer_name)}</span></div>
            <div className="info-row"><span className="info-label">Pre-Auth #</span><span className="info-value">{fmt(claim.insurance?.pre_auth_number)}</span></div>
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
          Claim ID: <strong style={{ color: 'var(--accent-primary)' }}>{claim.claim_id}</strong>
          &nbsp;•&nbsp; Type: {claim.input_type}
          &nbsp;•&nbsp; Status: {claim.meta?.status}
        </span>
      </div>

      <div className="action-bar">
        <button className="btn btn-secondary" onClick={onBack}>← Back</button>
        <button className="btn btn-primary" onClick={() => onComplete(null)}>
          Proceed to Policy Validation →
        </button>
      </div>
    </div>
  );
}
