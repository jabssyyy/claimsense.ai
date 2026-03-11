import { useState, useEffect } from 'react'
import { submitClaim, submitToInsurer } from '../api.js'

export default function SubmissionPage({ submissionData, onRestart }) {
  const [loading, setLoading] = useState(!submissionData?.claim);
  const [error, setError] = useState('');
  const [pkg, setPkg] = useState(null);
  const [submittedToInsurer, setSubmittedToInsurer] = useState(false);
  const [isSubmittingToInsurer, setIsSubmittingToInsurer] = useState(false);

  useEffect(() => {
    if (submissionData && !pkg) {
      runSubmission();
    }
  }, []);

  async function runSubmission() {
    setLoading(true);
    setError('');
    try {
      const claimJson = submissionData.validated_claim || submissionData.claim || {};
      const result = await submitClaim(
        claimJson,
        submissionData.validation_results || [],
        submissionData.coverage_summary || null,
      );
      setPkg(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <div className="loading-text">Running final quality checks...</div>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Verifying codes, documents, and assembling submission package
        </p>
      </div>
    );
  }

  if (!pkg) {
    return (
      <div className="page-header">
        <h1>Submission Package</h1>
        {error && <div className="error-banner">{error}</div>}
        <button className="btn btn-primary" onClick={runSubmission}>Retry</button>
      </div>
    );
  }

  const isReady = pkg.status === 'Ready for Submission';
  const fmtMoney = (v) => v ? `₹${Number(v).toLocaleString('en-IN')}` : '₹0';

  return (
    <div>
      <div className="page-header">
        <h1>
          {isReady ? 'Submission Package Ready' : 'Action Required'}
        </h1>
        <p>
          {isReady
            ? 'All checks passed — your claim is ready for submission'
            : 'Some issues need to be resolved before submission'
          }
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Status Banner */}
      <div style={{
        textAlign: 'center',
        marginBottom: 'var(--space-xl)',
        padding: 'var(--space-lg)',
        background: isReady ? 'var(--success-bg)' : 'var(--warning-bg)',
        border: `1px solid ${isReady ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)'}`,
        borderRadius: 'var(--radius-lg)',
      }}>
        <div style={{
          fontSize: 'var(--font-size-xl)',
          fontWeight: 700,
          color: isReady ? 'var(--success)' : 'var(--warning)',
        }}>
          {pkg.status}
        </div>
        {pkg.claim_reference && (
          <div style={{ marginTop: 'var(--space-sm)' }}>
            <span className="success-state">
              <span className="ref-number">{pkg.claim_reference}</span>
            </span>
          </div>
        )}
      </div>

      {/* Claim Summary Card */}
      <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
        <div className="card-title">Claim Summary</div>
        <div className="info-row"><span className="info-label">Claim ID</span><span className="info-value" style={{ color: 'var(--accent-primary)' }}>{pkg.claim?.claim_id}</span></div>
        <div className="info-row"><span className="info-label">Patient</span><span className="info-value">{pkg.claim?.patient?.name || '—'}</span></div>
        <div className="info-row"><span className="info-label">Hospital</span><span className="info-value">{pkg.claim?.hospital?.name || '—'}</span></div>
        <div className="info-row"><span className="info-label">Diagnosis</span><span className="info-value">{pkg.claim?.medical?.primary_diagnosis || '—'}</span></div>
        <div className="info-row"><span className="info-label">Total Bill</span><span className="info-value" style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>{fmtMoney(pkg.claim?.billing?.total_bill)}</span></div>
      </div>

      {/* Code Check Results */}
      {pkg.code_check_results?.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
          <div className="card-title">Medical Code Checks</div>
          <div className="validation-list">
            {pkg.code_check_results.map((r, i) => (
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
      )}

      {/* Document Check Results */}
      {pkg.document_check_results?.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
          <div className="card-title">Document Checklist</div>
          <div className="validation-list">
            {pkg.document_check_results.map((r, i) => (
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
      )}

      {/* Missing Items */}
      {pkg.missing_items?.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
          <div className="card-title" style={{ color: 'var(--danger)' }}>Items Requiring Action</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            {pkg.missing_items.map((item, i) => (
              <div key={i} className="missing-item">
                <span className="item-icon">
                  {item.item_type === 'document' ? 'DOC' : item.item_type === 'code' ? 'CODE' : '!'}
                </span>
                <div>
                  <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                    {item.item_name.replace(/_/g, ' ')}
                  </strong>
                  <div style={{ color: 'var(--text-secondary)' }}>{item.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Policy Validation Results from M2 */}
      {pkg.validation_results?.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
          <div className="card-title">Policy Validation (from Step 3)</div>
          <div className="validation-list">
            {pkg.validation_results.map((r, i) => (
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
      )}

      {/* Coverage Summary */}
      {pkg.coverage_summary && (
        <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
          <div className="card-title">Coverage Summary Report</div>
          <div className="summary-box">
            {pkg.coverage_summary.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        </div>
      )}

      <div className="action-bar">
        <button className="btn btn-secondary" onClick={onRestart}>
          Process New Claim
        </button>
        {isReady && !submittedToInsurer && (
          <button
            className="btn btn-success"
            disabled={isSubmittingToInsurer}
            onClick={async () => {
              setIsSubmittingToInsurer(true);
              setError('');
              try {
                const dbId = pkg.db_id;
                if (!dbId) throw new Error('No database ID found for this claim.');
                const result = await submitToInsurer(dbId);
                setSubmittedToInsurer(true);
              } catch (err) {
                setError(err.message);
              } finally {
                setIsSubmittingToInsurer(false);
              }
            }}
          >
            {isSubmittingToInsurer ? 'Submitting...' : 'Submit to Insurer'}
          </button>
        )}
        {submittedToInsurer && (
          <div style={{
            padding: '12px 20px',
            background: 'var(--success-bg)',
            border: '1px solid rgba(16,185,129,0.2)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--success)',
            fontWeight: 600,
            fontSize: 'var(--font-size-sm)',
          }}>
            Claim {pkg.claim_reference} has been successfully submitted to the insurer.
          </div>
        )}
      </div>
    </div>
  );
}

function formatRuleName(rule) {
  return rule
    .replace(/^doc_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}
